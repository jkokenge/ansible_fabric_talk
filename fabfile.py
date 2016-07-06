from fabric.api import *

env.hosts = ['45.56.75.32']
env.user  = 'root'

def remote_info():
    run('uname -a')

def local_info():
    local('uname -a')