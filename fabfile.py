from fabric.api import *

#fab command -i /path/to/key.pem [-H [user@]host[:port]]
#env.key_filename = '/path/to/keyfile.pem'

env.hosts = ['boot']
env.user  = 'root'

def remote_info():
    run('uname -a')

def local_info():
    local('uname -a')