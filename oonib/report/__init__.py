def generateReportID():
    return otime.timestamp() + '_' + randomStr(20)

class MissingField(Exception):
    pass

class InvalidRequestField(Exception):
    pass
