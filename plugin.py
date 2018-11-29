# -*- coding: utf-8 -*-
###
# Copyright (c) 2018, Bogdan Ilisei
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import log
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Darksky')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

import datetime
import calendar
from forecastiopy import *
import googlemaps

class Darksky(callbacks.Plugin):
    """Shows weather data using darksky.net (formerly forecast.io)"""
    threaded = True
    
    def _degrees_to_cardinal(self, d):
        """
        note: this is highly approximate...
        """
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        ix = int((d + 11.25)/22.5)
        return dirs[ix % 16]
 

    def forecast(self, irc, msg, args, location):
        """<location>

        Fetch forecast information from <location>.
        """
        
        channel = msg.args[0]

        darksky_api = self.registryValue('darksky_api')
        if not darksky_api:
            irc.error("No darksky.net API key.", Raise=True)

        geocode_api = self.registryValue('geocode_api')
        if not geocode_api:
            irc.error("No Google Geocode API key.", Raise=True)

        lang = self.registryValue('lang', channel=channel)
        units = self.registryValue('units', channel=channel)

        # Getting location information
        for i in range(0,10):
            try:
                gmaps = googlemaps.Client(key=geocode_api)
                loc = gmaps.geocode(location)
                my_loc = {}
                my_loc['lat'] = loc[0]['geometry']['location']['lat']
                my_loc['lng'] = loc[0]['geometry']['location']['lng']
                my_loc['formatted_address'] = loc[0]['formatted_address']
            except:
                print('Google API Error')
                continue


        # Getting forecast information
        try:
            print(my_loc)
            fio = ForecastIO.ForecastIO(darksky_api,
                                    units=units,
                                    lang=lang,
                                    latitude=my_loc['lat'],
                                    longitude=my_loc['lng'])
            print(format('URL: %s', fio.get_url()))
        except:
            irc.error('Weather API error', Raise=True)

        print(format('URL: %s', fio.get_url()))

        units = fio.flags['units']

        # Unit formatting
        if units != 'us':
            _tempU = '°C'
        else: 
            _tempU = '°F'

        if units == 'ca':
            _speedU = 'kph'
        elif units == 'si':
            _speedU = 'm/s'
        else:
            _speedU = 'mph'


        # Emoji!
        _icons = { 'clear-day': '☀️',
                'clear-night': '🌕',
                'rain': '🌧️',
                'snow': '❄️',
                'sleet': '🌧️❄️',
                'wind': '💨',
                'fog': '🌁',
                'cloudy': '☁️',
                'partly-cloudy-day': '🌤️',
                'partly-cloudy-night': '☁️',
                'thunderstorm': '⛈️',
                'tornado': '🌪'
                }

        now_summary = ''

        if fio.has_minutely() is True:
            minutely = FIOMinutely.FIOMinutely(fio)
            now_summary = minutely.summary
        elif fio.has_hourly() is True:
            hourly = FIOHourly.FIOHourly(fio)
            now_summary = hourly.summary

        # Current Conditions
        if fio.has_currently() is True:
            currently = FIOCurrently.FIOCurrently(fio)
            
            if not now_summary:
                now_summary = currently.summary

            now = format('%s: %s%s (≈%s%s). %s %s Hum: %s%%, Wind: %s%s %s',
                    ircutils.bold(my_loc['formatted_address']),
                    int(currently.temperature), _tempU,
                    int(currently.apparentTemperature), _tempU,
                    _icons[currently.icon],
                    now_summary,
                    int(currently.humidity * 100),
                    int(currently.windSpeed), _speedU,
                    self._degrees_to_cardinal(currently.windBearing),
                    )

        if fio.has_daily() is True:
            daily = FIODaily.FIODaily(fio)

            overall = format('%s%s',
                    _icons[daily.icon],
                    daily.summary
                    )
            
            day_2 = daily.get_day(2)
            tomorow_name = calendar.day_name[ datetime.datetime.utcfromtimestamp(day_2['time']).weekday() ]

            tomorow = format('%s: %s%s Min: %s%s/%s%s Max: %s%s/%s%s',
                    ircutils.underline(tomorow_name),
                    _icons[day_2['icon']],
                    day_2['summary'],
                    int(day_2['temperatureLow']), _tempU,
                    int(day_2['apparentTemperatureLow']), _tempU,
                    int(day_2['temperatureHigh']), _tempU, 
                    int(day_2['apparentTemperatureHigh']), _tempU,
                    )

            day_3 = daily.get_day(3)
            dat_name = calendar.day_name[ datetime.datetime.utcfromtimestamp(day_3['time']).weekday() ]

            dat =    format('%s: %s%s Min: %s%s/%s%s Max: %s%s/%s%s',
                    ircutils.underline(dat_name),
                    _icons[day_3['icon']],
                    day_3['summary'],
                    int(day_3['temperatureLow']), _tempU,
                    int(day_3['apparentTemperatureLow']), _tempU,
                    int(day_3['temperatureHigh']), _tempU,
                    int(day_3['apparentTemperatureHigh']), _tempU,
                    )
                    
        irc.reply(now + ' ' + overall + ' ' + tomorow + '. ' + dat)

    forecast = wrap(forecast, ['text'])

Class = Darksky


# vim:set shiftwidth=4 softtabstop=4 expandtab:
