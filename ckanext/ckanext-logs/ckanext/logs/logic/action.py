import base64
import logging
from datetime import datetime, timedelta

import requests

import ckan.plugins.toolkit as tk
from ckan.common import _, config
from ckan.lib.helpers import helper_functions as h
from ckan.types import Context, DataDict

from .. import helpers as logs_helpers

log = logging.getLogger(__name__)

@tk.side_effect_free
def show_logs(context: Context, data_dict: DataDict): # type: ignore
    tk.check_access("show_logs", context, data_dict)
    
    q = data_dict.get('q', '')
    default_limit: int = config.get('ckan.logs.limit', 10)
    limit = int(data_dict.get('limit', default_limit))
    page = data_dict.get('page', 1)
    page = int(page)
    offset = (page - 1) * limit
    
    display_tz = h.get_display_timezone()
    current_date = datetime.now(display_tz)
    start_time_input = data_dict.get('start_time', '')
    end_time_input = data_dict.get('end_time', '')
    
    if start_time_input == '' and end_time_input == '':
        start_time = (current_date - timedelta(days=30)).strftime("%Y-%m-%d")
        end_time = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
    elif logs_helpers.validate_date_range(start_time_input, end_time_input):
        start_time = datetime.strptime(start_time_input, '%Y-%m-%d').strftime("%Y-%m-%d")
        end_time = (datetime.strptime(end_time_input, '%Y-%m-%d') + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        return {"error": _(u'Date format incorrect')}
    
    log_host = config.get('ckan.logs.url')
    log_index = '-'.join([config.get('ckan.logstash.message_type'), '*']) # not update for search with date
    url = '/'.join([log_host, log_index, '_search'])

    log_auth = ':'.join([config.get('ckan.logs.username', ''), config.get('ckan.logs.password', '')]) 
    headers = {
        'Content-Type': 'application/json',
        'Authorization': ' '.join(['Basic', base64.b64encode(log_auth.encode('utf-8')).decode('utf-8')]),
    }

    body={
        "query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte":start_time, 
                                "lt":end_time
                            }
                        }
                    }
                ]
            }
        },
        "sort": [
            {
                "@timestamp": {
                    "order": "desc"
                }
            }
        ],
        "from": offset,
        "size": limit
    }
    
    if q != '':
        body['query']['bool']['must'].append({
            "match": {
                "message": q
            }
        })
    
    response = requests.request("POST", url, headers=headers, json = body)
    try:
        if response.status_code == 200:
            date_obj = datetime.strptime(end_time, "%Y-%m-%d")
            end_time = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
            
            data = response.json()
            result = {
                'q': q,
                'start_time': start_time,
                'end_time': end_time,
                'total' : 0,
                'data' : []
            }
            result['total'] = data['hits']['total']['value']
            result['data'] = data['hits']['hits']         
            return result
    except Exception as e:
        log.error("Get data logs fail! %s", e)
    return {"error": _(u'Error loading logs')}

def get_actions():
    return {
        'show_logs': show_logs,
    }
