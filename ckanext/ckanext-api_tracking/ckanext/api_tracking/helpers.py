import hashlib
import six
import re
from ckan.types import CKANApp
import ckan.model.meta as meta
import ckan.model as model

def generate_user_key(environ):
    try:
        user_agent = environ.get('HTTP_USER_AGENT', 'unknown')
        remote_addr = environ.get('REMOTE_ADDR', 'unknown')
        accept_language = environ.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = environ.get('HTTP_ACCEPT_ENCODING', '')

        key = ''.join([user_agent, remote_addr, accept_language, accept_encoding])
        return hashlib.md5(six.ensure_binary(key)).hexdigest()
    except Exception as e:
        CKANApp.logger.error(f"Error generating user key: {e}")
        return None

def get_data_type(url):
    try:
        if check_resource(url):
            return 'resource'
        elif check_dataset(url):
            return 'page'
        return None
    except Exception as e:
        CKANApp.logger.error(f"Error getting data type: {e}")
        return None

def check_dataset(url):
    try:
        pattern1 = r'^/dataset/([^/]+)$'
        # pattern2 = r'^/dataset/([^/]+)/resource/([^/]+)$'
        match1 = re.match(pattern1, url)
        # match2 = re.match(pattern2, url)
            
        if match1:
            package_name = match1.group(1) 
            dataset = meta.Session.query(model.Package
                                         ).filter(model.Package.name == package_name).first()                
            return dataset is not None
        
    except Exception as e:
        CKANApp.logger.error(f"Error checking dataset: {e}")
            
    return False

def check_resource(url):
    try:
        pattern = r'^(.*/resource/([^/]+)/download/.*)'
        match = re.match(pattern, url)
        if match:
            resource_id = match.group(2)
            package_id = url.split('/resource/')[0].split('/')[-1]
            resource_name = url.split('/download/')[1]
            resource = meta.Session.query(model.Resource).filter(
                model.Resource.id == resource_id,
                model.Resource.package_id == package_id,
                model.Resource.url == resource_name
            ).first()

            return resource is not None
    except Exception as e:
        CKANApp.logger.error(f"Error checking resource: {e}")
        
    return False
