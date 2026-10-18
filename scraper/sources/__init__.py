from .ats import greenhouse, lever, smartrecruiters, workday
from .bigtech import amazon, microsoft
from .boards import jsearch, linkedin, remoteok, remotive
from .email_alerts import email_alerts

# Display names used on the web page.
SOURCES = {
    "workday": (workday, "Workday"),
    "greenhouse": (greenhouse, "Greenhouse"),
    "lever": (lever, "Lever"),
    "smartrecruiters": (smartrecruiters, "SmartRecruiters"),
    "amazon": (amazon, "Amazon"),
    "microsoft": (microsoft, "Microsoft"),
    "linkedin": (linkedin, "LinkedIn"),
    "email_alerts": (email_alerts, "Email alerts"),
    "jsearch": (jsearch, "Google Jobs"),
    "remotive": (remotive, "Remotive"),
    "remoteok": (remoteok, "RemoteOK"),
}
