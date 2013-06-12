import os
from subprocess import Popen, PIPE
from docviewer.settings import IMAGE_FORMAT, DOCSPLIT_PATH
from docviewer.models import Document
from datetime import datetime
import shutil

from django.utils.translation import ugettext as _
from django.db import models

#FIXME : haystack error cannot import article

from article.models import Article
from bibliography.models import Bibliography, BpIssue
from document.models import Document as FuturiblesDocument
from revue.models import RevueIssue, RevueArticle

def docsplit(document):
    
    path = document.get_root_path()
    commands = [DOCSPLIT_PATH + "docsplit images --size 700x,1000x,180x --format %s --output %s %s/%s.pdf" % (IMAGE_FORMAT,path, path,document.slug), 
                DOCSPLIT_PATH + "docsplit text --pages all --output %s %s/%s.pdf" % (path, path,document.slug)]
    
    if document.filename.split('.')[-1].lower() != 'pdf':
        cmd = DOCSPLIT_PATH + "docsplit pdf --output %s %s" % (path, document.get_file_path())
        commands.insert(0, cmd)
    
    for command in commands:
        result = Popen(command, shell=True, stdout=PIPE).stdout.read()
        
        if len(result) > 0:
            raise Exception(result)
        
    # rename directories
    #FIXME
    shutil.rmtree("%s/%s" % (path, "large"), ignore_errors=True)
    os.rename("%s/%s" % (path, "1000x"), "%s/%s" % (path, "large"))
    
    shutil.rmtree("%s/%s" % (path, "normal"), ignore_errors=True)
    os.rename("%s/%s" % (path, "700x"), "%s/%s" % (path, "normal"))
    
    shutil.rmtree("%s/%s" % (path, "small"), ignore_errors=True)
    os.rename("%s/%s" % (path, "180x"), "%s/%s" % (path, "small"))    

def create_document(filepath, doc_attributes):
    
    d = Document(**doc_attributes)
    d.save()
    
    d.set_file(filepath)
    
    return d


def generate_document(doc_id,  task_id=None):
    
    document = Document.objects.get(pk=doc_id)
        
    if task_id is not None and document.task_id != task_id:
        raise Exception("Celery task ID doesn't match")
    
    document.status = Document.STATUS.running
    document.task_start = datetime.now()
    document.save()
    try:
        docsplit(document)
    
        document.generate()
        document.status = document.STATUS.ready
        document.task_id = None
        document.task_error = None
        document.save()
        
        #FIXME : haystack error cannot import article
        try:
            article = Article.objects.get(docviewer=document)
            article.save()
        except Article.DoesNotExist:
            pass

        try:
            bibliography = Bibliography.objects.get(docviewer=document)
            bibliography.save()
        except Bibliography.DoesNotExist:
            pass

        try:
            bp_issue = BpIssue.objects.get(docviewer=document)
            bp_issue.save()
        except BpIssue.DoesNotExist:
            pass

        try:
            futuribles_document = FuturiblesDocument.objects.get(docviewer=document)
            futuribles_document.save()
        except FuturiblesDocument.DoesNotExist:
            pass

        try:
            revue_issue = RevueIssue.objects.get(docviewer=document)
            revue_issue.save()
        except RevueIssue.DoesNotExist:
            pass

        try:
            revue_article = RevueArticle.objects.get(docviewer=document)
            revue_article.save()
        except RevueArticle.DoesNotExist:
            pass
        

    except Exception, e:
        
        try:
            document.task_error = str(e)
            document.status = document.STATUS.failed
            document.save()
        except:
            pass
        
        raise
