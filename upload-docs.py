import os

cmd = 'rsync -avz build/sphinx/html/ kforge@us0.okfn.org:~/knowledgeforge.net/var/project_data/ckan/www/doc/ckan'
print cmd
os.system(cmd)

