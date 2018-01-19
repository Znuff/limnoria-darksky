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
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Darksky')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


from forecastiopy import *
from geolocation.main import GoogleMaps

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

        darksky_api = self.registryValue('darksky_api')
        if not darksky_api:
            irc.error("No darksky.net API key.", Raise=True)

        geocode_api = self.registryValue('geocode_api')
        if not geocode_api:
            irc.error("No Google Geocode API key.", Raise=True)

        lang = self.registryValue('lang')
        units = self.registryValue('units')

        # Getting location information
        google_maps = GoogleMaps(api_key=geocode_api)
        loc = google_maps.search(location=location)
        my_loc = loc.first()

        # Getting forecast information
        fio = ForecastIO.ForecastIO(darksky_api,
                                    units=units,
                                    lang=lang,
                                    latitude=my_loc.lat,
                                    longitude=my_loc.lng)

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

            now = format('%s: %s%s (feels like %s%s). %s Hum: %s%%, Wind: %s%s %s',
                    ircutils.bold(my_loc.formatted_address),
                    int(currently.temperature), _tempU,
                    int(currently.apparentTemperature), _tempU,
                    now_summary,
                    int(currently.humidity * 100),
                    int(currently.windSpeed), _speedU,
                    self._degrees_to_cardinal(currently.windBearing),
                    )

        irc.reply(now)


    forecast = wrap(forecast, ['text'])

Class = Darksky


# vim:set shiftwidth=4 softtabstop=4 expandtab:
