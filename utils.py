def distance(preference, distance):
    if preference == "meters":
        return distance
    else:
        return distance * 0.621371

def elevation(preference, elevation):
    if preference == "meters":
        return "{:,} m".format(int("%.0f" % elevation))
    else:
        return "{:,} ft".format(int("%.0f" % (elevation * 3.28084)))

def moving_time(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%02dh %02dm" % (h, m)

def commutes_percentage(count, total):
    if total == 0:
        return "0 %"
    else:
        return "%.0f %%" % (float(count)/float(total) * 100)

def days_left():
    from datetime import date
    from calendar import monthrange
    today = date.today()
    
    range = monthrange(today.year, today.month)
    return range[1] - today.day

