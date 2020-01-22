YEARS_PER_DAY = 1 / 365.25

PYRATE_DEFAULT_CONFIGRATION = {
    "obsdir": {
        "DataType": "path",
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "ifgfilelist": {
        "DataType": "path",
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "demfile": {
        "DataType": "path",
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "demHeaderFile": {
        "DataType": "path",
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "slcFileDir": {
        "DataType": "path",
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "slcfilelist": {
        "DataType": "path",
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "cohfiledir": {
        "DataType": "path",
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "cohfilelist": {
        "DataType": "path",
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "outdir": {
        "DataType": "path",
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "processor": {
        "DataType": int,
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [0, 1]
    },
    "noDataAveragingThreshold": {
        "DataType": float,
        "DefaultValue": 0.0,
        "MinValue": 0,
        "MaxValue": None,
        "PossibleValues": None
    },
    "noDataValue": {
        "DataType": float,
        "DefaultValue": 0.0,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "nan_conversion": {
        "DataType": int,
        "DefaultValue": 0,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [0, 1]
    },
    "parallel": {
        "DataType": int,
        "DefaultValue": 0,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [0, 1, 2]
    },
    "processes": {
        "DataType": int,
        "DefaultValue": 8,
        "MinValue": 1,
        "MaxValue": None,
        "PossibleValues": None
    },
    "cohmask": {
        "DataType": int,
        "DefaultValue": 0,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [0, 1]
    },
    "cohthresh": {
        "DataType": float,
        "DefaultValue": 0.1,
        "MinValue": 0.0,
        "MaxValue": 1.0,
        "PossibleValues": None
    },
    "ifgcropopt": {
        "DataType": int,
        "DefaultValue": 1,
        "MinValue": 1,
        "MaxValue": 4,
        "PossibleValues": [1, 2, 3, 4]
    },
    "ifglksx": {
        "DataType": int,
        "DefaultValue": 1,
        "MinValue": 1,
        "MaxValue": None,
        "PossibleValues": None
    },
    "ifglksy": {
        "DataType": int,
        "DefaultValue": 1,
        "MinValue": 1,
        "MaxValue": None,
        "PossibleValues": None
    },
    "ifgxfirst": {
        "DataType": float,
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "ifgxlast": {
        "DataType": float,
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "ifgyfirst": {
        "DataType": float,
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "ifgylast": {
        "DataType": float,
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "refx": {
        "DataType": float,
        "DefaultValue": -1,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "refy": {
        "DataType": float,
        "DefaultValue": -1,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": None
    },
    "refnx": {
        "DataType": int,
        "DefaultValue": 10,
        "MinValue": 1,
        "MaxValue": 50,
        "PossibleValues": None
    },
    "refny": {
        "DataType": int,
        "DefaultValue": 10,
        "MinValue": 1,
        "MaxValue": 50,
        "PossibleValues": None
    },
    "refchipsize": {
        "DataType": int,
        "DefaultValue": 21,
        "MinValue": 1,
        "MaxValue": 101,
        "PossibleValues": None,
        "Note": "Must be an odd number."
    },
    "refminfrac": {
        "DataType": float,
        "DefaultValue": 0.5,
        "MinValue": 0.0,
        "MaxValue": 1.0,
        "PossibleValues": None
    },
    "refest": {
        "DataType": int,
        "DefaultValue": 1,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [1, 2]
    },
    "orbfit": {
        "DataType": int,
        "DefaultValue": 0,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [0, 1]
    },
    "orbfitmethod": {
        "DataType": int,
        "DefaultValue": 2,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [1, 2]
    },
    "orbfitdegrees": {
        "DataType": int,
        "DefaultValue": 1,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [1, 2, 3]
    },
    "orbfitlksx": {
        "DataType": int,
        "DefaultValue": 10,
        "MinValue": 1,
        "MaxValue": None,
        "PossibleValues": None
    },
    "orbfitlksy": {
        "DataType": int,
        "DefaultValue": 10,
        "MinValue": 1,
        "MaxValue": None,
        "PossibleValues": None
    },
    "apsest": {
        "DataType": int,
        "DefaultValue": 0,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [0, 1]
    },
    "slpfmethod": {
        "DataType": int,
        "DefaultValue": 1,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [1, 2]
    },
    "slpfcutoff": {
        "DataType": float,
        "DefaultValue": 1.0,
        "MinValue": 0.001,
        "MaxValue": None,
        "PossibleValues": None
    },
    "slpforder": {
        "DataType": int,
        "DefaultValue": 1,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [1, 2, 3]
    },
    "slpnanfill": {
        "DataType": int,
        "DefaultValue": 0,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [0, 1]
    },
    "slpnanfill_method": {
        "DataType": str,
        "DefaultValue": "cubic",
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": ["linear", "nearest", "cubic"]
    },
    "tlpfmethod": {
        "DataType": int,
        "DefaultValue": 1,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [1, 2, 3]
    },
    "tlpfcutoff": {
        "DataType": float,
        "DefaultValue": 1.0,
        "MinValue": YEARS_PER_DAY,
        "MaxValue": None,
        "PossibleValues": None
    },
    "tlpfpthr": {
        "DataType": int,
        "DefaultValue": 1,
        "MinValue": 1,
        "MaxValue": None,
        "PossibleValues": None
    },
    "tscal": {
        "DataType": int,
        "DefaultValue": 0,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [0, 1]
    },
    "tsmethod": {
        "DataType": int,
        "DefaultValue": 2,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [1, 2]
    },
    "smorder": {
        "DataType": int,
        "DefaultValue": None,
        "MinValue": None,
        "MaxValue": None,
        "PossibleValues": [1, 2]
    },
    "smfactor": {
        "DataType": float,
        "DefaultValue": -1.0,
        "MinValue": -5.0,
        "MaxValue": 0,
        "PossibleValues": None
    },
    "ts_pthr": {
        "DataType": int,
        "DefaultValue": 3,
        "MinValue": 1,
        "MaxValue": None,
        "PossibleValues": None
    },
    "nsig": {
        "DataType": int,
        "DefaultValue": 2,
        "MinValue": 1,
        "MaxValue": 10,
        "PossibleValues": None
    },
    "pthr": {
        "DataType": int,
        "DefaultValue": 3,
        "MinValue": 1,
        "MaxValue": None,
        "PossibleValues": None
    },
    "maxsig": {
        "DataType": int,
        "DefaultValue": 10,
        "MinValue": 0,
        "MaxValue": 1000,
        "PossibleValues": None
    }
}