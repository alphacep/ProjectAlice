"""
Use double quotes!
"""

settings = {
	"ssid": "",
	"wifipassword": "",
	"mqttHost": "localhost",
	"mqttPort": "1883",
	"micSampleRate": 44100,
	"micChannels": 1,
	"enableDataStoring": False,
	"autoPruneStoredData": 0, # Set to max entries to keep, 0 to disable pruning
	"probabilityTreshold": 0.45,
	"stayCompletlyOffline": False,
	"keepASROffline": False,
	"keepTTSOffline": False,
	"shortReplies": False,
	"whisperWhenSleeping": True,
	"newDeviceBroadcastPort": 12354,
	"intentsOwner": "",
	"asr": "snips",
	"tts": "pico",
	"ttsLanguage": "en-US",
	"ttsType": "male",
	"ttsVoice": "en-US", # The name of the voice on the TTS service
	"awsRegion": "eu-central-1",
	"awsAccessKey": "",
	"awsSecretKey": "",
	"useSLC": False,
	"activeLanguage": "en",
	"activeCountryCode": "US",
	"moduleAutoUpdate": False,
	"githubUsername": "",
	"githubToken": "",
	"supportedLanguages": {
		"en": {
			"snipsProjectId" : "",
			"default": True,
			"countryCode": 'US'
		},
		"fr": {
			"snipsProjectId" : "",
			"default": False,
			"countryCode": 'FR'
		},
		"de": {
			"snipsProjectId" : "",
			"default": False,
			"countryCode": 'DE'
		}
	},

	"snipsConsoleLogin": "",
	"snipsConsolePassword": "",

	"baseCurrency": "CHF",
	"baseUnits": "metric", # metric, kelvin or imperial

	"onReboot": "", # This is for system use only

	"webInterfaceActive": False,
	"webInterfacePort": 5000,

	#-----------------------
	# Modules
	#-----------------------

	"modules": {
		"AliceCore": {
			"active"    : True,
			"version"   : 1.10,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		},
		"AliceSatellite": {
			"active"    : True,
			"version"   : 1.0,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		},
		"ContextSensitive": {
			"active"    : True,
			"version"   : 1.0,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		},
		"Customisation": {
			"active"    : True,
			"version"   : 1.01,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		},
		"DateDayTimeYear": {
			"active"    : True,
			"version"   : 1.01,
			"author"    : "Psychokiller1888",
			"conditions": {
				"lang": [
					"en",
					"fr",
					"de"
				]
			}
		},
		"RedQueen": {
			"active"    : True,
			"version"   : 1.04,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		}
	}
}
