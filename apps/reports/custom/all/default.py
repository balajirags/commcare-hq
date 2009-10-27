from datetime import datetime, timedelta

from django.template.loader import render_to_string

from xformmanager.models import Metadata
from graphing.dbhelper import DbHelper
from hq.utils import get_dates


"""Where to put default global reports.  These behave just like custom reports
   except they are available to all domains.  If you don't want these reports
   to show up for your domain you should create a <domain>.py file in this 
   folder and explicitly point to any reports you want to include."""
# TODO: we have a lot of reports directories and custom/global/default is
# a pretty obnoxious namespace.  Possibly figure out a better way to 
# organize these if it becomes to burdensome

def blacklist(request, domain=None):
    '''Report of who is submitting as blacklisted users'''
    if not domain:
        domain = request.extuser.domain
    startdate, enddate = get_dates(request, 7)
    if enddate < startdate:
        return '''<p><b><font color="red">The date range you selected is not valid.  
                  End date of %s must fall after start date of %s.</font></b></p>'''\
                  % (enddate, startdate)
    
    # our final structure called "all_data" will be:
    # { blacklist_username1: 
    #    { device_id1: 
    #        { # counts of submissions from the blacklisted user by date
    #          "date_counts": {date1: count1, date2: count2...} 
    #          # other users who have also submitted from that device
    #          "users": [user1, user2] 
    #        }
    #      device_id2: { ... }
    #      ...
    #    }
    #   blacklist_username2: { ... }
    #   ...
    # }
    # yikes.  we'll build it from the outside in, starting with the blacklist
    
    all_data = {}
    domain_blacklist = domain.get_blacklist()
    
    # we need this dbhelper to do our inner queries, but might as well only
    # initialize it once. 
    # TODO: we must be able to get the tablename, description from the model meta 
    dbhelper = DbHelper("xformmanager_metadata", "XForm Metadata", "timeend")
        
    for blacklisted_user in domain_blacklist:
        # get metas, in the domain, within the timespan, matching this user
        all_metas = Metadata.objects.filter(timeend__gte=startdate)\
                        .filter(timeend__lte=enddate)\
                        .filter(attachment__submission__domain=domain)\
                        .filter(username=blacklisted_user)
        
        # list of devices submitting from this user in the period
        devices_to_check = all_metas.values_list('deviceid', flat=True).distinct()
        this_user_device_data = {}
        for device in devices_to_check:
            counts = dbhelper.get_filtered_date_count(startdate, enddate, 
                                             {"username": blacklisted_user,
                                              "deviceid": device })
            # flip key, value around and turn into a dictionary
            dict_counts = dict([(val, key) for key, val in  counts])
            users = Metadata.objects.filter(deviceid=device)\
                        .exclude(username=blacklisted_user)\
                        .values_list('username', flat=True).distinct()
            clean_users = []
            for user in users:
                if user:
                    clean_users.append(user)
                else:
                    clean_users.append("EMPTY USERNAME")
            this_device_data = {"date_counts": dict_counts,
                                "users": ",".join(clean_users)}
            this_user_device_data[device] = this_device_data
        all_data[blacklisted_user] = this_user_device_data
            
    totalspan = enddate - startdate
    date_headings = [] 
    for day in range(0,totalspan.days+1):
        target_date = startdate + timedelta(days=day)
        date_headings.append(target_date.strftime('%m/%d/%Y'))
    return render_to_string("custom/all/blacklist_submissions.html", 
                            {"all_dates": date_headings, 
                             "all_data": all_data, 
                             "startdate": startdate,
                             "enddate": enddate,
                             "domain": domain})
