import sys
import os
import urllib2
import shutil
import re

import tempfile as tmp
from zipfile import ZipFile 
from cStringIO import StringIO

from subprocess import Popen, PIPE

# import re
# import logging

# from buildmanager import xformvalidator
# from buildmanager.exceptions import BuildError

# from xformmanager.models import MetaDataValidationError
# from xformmanager.xformdef import FormDef, ElementDef


def add_to_jar(jar_file, path_to_add):
    '''adds files under /path_to_add to jar_file, return path to the new JAR'''
    if not os.path.isdir(path_to_add):
        raise "Trying to add non-existant directory '%s' to JAR" % str(path_to_add)
        
    if not jar_file.endswith('.jar') or not os.path.isfile(jar_file):
        raise "'%s' isn't a JAR file" % jar_file

    tmpjar = os.path.join(tmp.mkdtemp(), os.path.basename(jar_file))
    shutil.copy2(jar_file, tmpjar)
    
    zf = ZipFile(tmpjar, 'a')
    
    for f in os.listdir(path_to_add):
        full_path = os.path.join(path_to_add, f)
        if os.path.isdir(full_path): continue
        zf.write(full_path, str(f))
        
    zf.close
    
    return tmpjar


def modify_jad(jad_file, jar_file):
    # read JAD to dict
    jad = {}
    for line in open(jad_file).readlines():
        key, val = line.split(':',1)
        jad[key] = val.strip()
    
    # modify JAD data 
    jad['MIDlet-Jar-Size'] = os.path.getsize(jar_file)
    jad['MIDlet-Jar-URL']  = os.path.basename(jar_file)

    # create new JAD
    new_content = ''
    for i in jad:
        new_content += "%s: %s\n" % (i, jad[i])
    
    x, tmpjad = tmp.mkstemp() 
    f = open(tmpjad, 'w')
    f.write(new_content)
    f.close()
    
    return tmpjad
    
    
def create_zip(target, files):
    ''' create zip from files list, returns created zip file'''
    zf = ZipFile(target, 'w')
    for f in files:
        zf.write(f)
    
    zf.close()
    return target
    
    
# http://bitbucket.org/ctsims/resourcetest/get/tip.zip
def grab_from(url):
    '''copy a file from a URL to a local tmp dir, returns path to local copy'''
    u = urllib2.urlopen(url)
    u = u.read()
    
    x, tmpfile = tmp.mkstemp()
    f = open(tmpfile, 'w')
    f.write(u)
    f.close()
    
    return tmpfile


def unzip(zip_file, target_dir=None):
    '''
    extracts a resources zip.
    assumes that all files are on one root dir
    returns path of extracted files
    '''
    zf = ZipFile(zip_file)
    if target_dir is None:
        target_dir = tmp.mkdtemp()
    elif not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    namelist = zf.namelist()
    filelist = filter( lambda x: not x.endswith( '/' ), namelist )

    for filename in filelist:
        basename = os.path.basename(filename)
        if basename.startswith('.'): continue #filename.endswith(".xml") or filename.endswith(".xhtml"):

        target_file = os.path.join(target_dir, basename)

        out = open(target_file, 'wb')

        buffer = StringIO( zf.read(filename))
        buflen = 2 ** 20
        datum = buffer.read(buflen)

        while datum:
            out.write(datum)
            datum = buffer.read(buflen)
        out.close()
        
    return target_dir


def clone_from(url):
    if re.match(r'http:\/\/.*bitbucket.org\/', url) is not None:
        # hg won't clone to an existing directory, and tempfile won't return just a name without creating a dir
        # so just delete the new tmp dir and let hg recreate it in clone
        tmpdir = tmp.mkdtemp()
        os.rmdir(tmpdir)

        # obviously, this depends on a particular URL format.
        # if we stick with bitbucket, standardize on an expected URL.
        hg_root, path = url.split('/src')
        path = path.replace('/tip', '')
        path = path.lstrip('/') # dont confuse os.path.join
        
        clone_cmd = ["hg", "clone", hg_root, tmpdir]
        p = Popen(clone_cmd, stdout=PIPE, stderr=PIPE, shell=False)
        err = p.stderr.read().strip()
        
        if err != '': raise err

        return os.path.join(tmpdir, path)

    else:
        raise "Unknown SCM URL"
    

# unused for now. move it later to a short_url app as HQ-wide service.
def get_bitly_url_for(url):
    try:
        bitly_login  = settings.RAPIDSMS_APPS['releasemanager']['bitly_login']
        bitly_apikey = settings.RAPIDSMS_APPS['releasemanager']['bitly_apikey']
    except:
        return false

    bitly_url = "http://api.bit.ly/v3/shorten?login=dmgi&apiKey=R_af7d5c0d899197fe43e18acceebd5cdb&uri=%s&format=txt" % url
    
    u = urllib2.urlopen(bitly_url)
    short_url = u.read().strip()
    
    if short_url == '': return false
    
    return short_url
    
        
