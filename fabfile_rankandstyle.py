import os
import sys
p = os.path.dirname(__file__)
sys.path.insert(0, p)

from cStringIO import StringIO

from fabric.api import env, cd, task, run, local, prompt, get
from fabric.contrib.project import rsync_project
from fabric.contrib import django

from time import time

django.project('rns')
from django.conf import settings


env.user = 'rns'
env.hosts = ['otacon.rankandstyle.com']

# Production database credentials
# Not using settings.py because the conf can be overridden locally.

os.chdir(os.path.dirname(env['real_fabfile']))

rsync_exclude = ('.hg*', 'fabfile.*', '*.pyc', '.DS_Store', '.venv', '.ropeproject', 'media', 'static/-/')


def panic_if_production():
    if os.path.expanduser('~') == '/home/rns':
        raise OSError('Panicking because on production server!')


@task()
def update():
    """Legacy task for updating the production server.  Preserved for history.

    """
    return
    rsync_project('/home/rns/site', exclude=rsync_exclude, delete=True, extra_opts='-t')
    with cd('/home/rns/site/rankandstyle.com/rns'):
        run('./manage.py collectstatic --verbosity=0 --noinput --link')
        run('touch rns/wsgi.py')
        run('./manage.py clearcache')


@task
def update_local_db(nosouth=False, noprompt=False):
    """Pulls the live DB and updates the local DB.

    """
    panic_if_production()
    db_conf = settings.DATABASES['default']

    print ('\033[93m/!\\ This is a destructive operation!  '
               'Your local database defined in settings.py will be overwritten! '
               '/!\\\033[0m')

    if not noprompt:
        confirm = prompt(('Are you sure you want to update the local dev database '
                         '({USER}@{HOST}/{NAME}) '
                         'with the remote production database?').format(**db_conf),
                         default='y/N')
        if confirm.lower() != 'y':
            print 'Canceled!'
            return

    db_archive = '/tmp/{}.{}.sql.gz'.format(env.db_name, int(time()))
    mysql_dump = 'mysqldump --user {} --password={} {} '.format(env.db_user,
                                                                env.db_passwd,
                                                                env.db_name)

    mysql_dump = mysql_dump + '--ignore-table {}.django_session '.format(env.db_name)

    if nosouth:
        mysql_dump = mysql_dump + '--ignore-table={}.south_migrationhistory '.format(env.db_name)
    mysql_dump = mysql_dump + '| gzip > {}'.format(db_archive)

    run(mysql_dump)
    get(db_archive, db_archive)
    run('rm {}'.format(db_archive))

    if not db_conf.get('PASSWORD', False):
        mysql_update = 'gunzip < {} | mysql -u {} -D {}' \
                       .format(db_archive, db_conf['USER'], db_conf['NAME'])
    else:
        mysql_update = 'gunzip < {} | mysql -u {} -p{} -D {}' \
                       .format(db_archive, db_conf['USER'],
                                db_conf['PASSWORD'], db_conf['NAME'])

    local(mysql_update)
    local('rm {}'.format(db_archive), capture=False)


@task
def dbtest():
    pass


@task
def update_media(noprompt=False):
    """Updates the local media directory with the contents of the production
    media directory.
    """
    panic_if_production()
    print '\033[93mLocal Media: {}\033[0m'.format(settings.MEDIA_ROOT)
    if not noprompt:
        confirm = prompt(('Are you sure you want to update local media files '
                          'with production media files?'), default='y/N')
        if confirm.lower() != 'y':
            print 'Canceled'
            return

    local('rsync -avz rns@otacon.rankandstyle.com:/home/rns/application/media/ "{}"'.format(settings.MEDIA_ROOT))


@task
def update_all(nosouth=False, noprompt=False):
    update_local_db(nosouth=nosouth, noprompt=noprompt)
    update_media(noprompt=noprompt)


@task
def rewardstyle_auth(code=''):
    if not code:
        print 'Need code'
        sys.exit(1)

    import requests
    client = '3dbaa38fbc94858db7c7d127fb2dc35462fd54f5aa2faa37'
    secret = '38fbc949ec52b6f87225cdcb0eb8ebd57baa035aa3709295'

    payload = {
        'client_id': client,
        'client_secret': secret,
        'code': code,
    }

    r = requests.post('https://api.rewardstyle.com/oauth/token', data=payload)
    print r.status_code
    print r.text


@task
def dump_tags():
    from taggit.models import Tag, TaggedItem
    for t in Tag.objects.all().order_by('name'):
        if t.name:
            t2 = TaggedItem.objects.filter(tag=t)
            c = t2.count()
            print '"%s","%d"' % (t.name.encode('utf8'), c)


def print_varnish_headers(fd):
    http_status = ''
    headers = []
    for line in fd.getvalue().split('\n'):
        i = line.find('out: ')
        if i == -1:
            continue
        line = line[i+5:].strip()
        if not line:
            continue
        if line.find(':') != -1:
            headers.append(line)
        elif line.find('HTTP') != -1:
            http_status = line
    headers.sort()
    print http_status
    print '\n'.join(headers)


@task
def varnish_headers(url):
    stdout = StringIO()
    run('curl -s -D - "http://127.0.0.1%s" -o /dev/null' % url, stdout=stdout)
    print_varnish_headers(stdout)


@task
def varnish_purge(url):
    stdout = StringIO()
    run('curl -s -D - -X PURGE "http://127.0.0.1%s" -o /dev/null' % url, stdout=stdout)
    print_varnish_headers(stdout)


# Export tables:
# django_flatpage
# faq_question
# faq_topic
# rscms_saveddata
# south_migrationhistory
# webmodules_listmodule
# webmodules_productmodule
# webmodules_promotionmodule
# webmodules_websitemodule
# website_category
# website_faq
# website_influencerlist
# website_influencerqa
# website_influencerslide
# website_list_categories
# website_popularproducts
# website_shoppablegallery
# website_shoppablegallery_items
# website_shoppablegalleryitem
# website_testimonial
# websitemeta_websitemeta
# websitesearch_useractivity
