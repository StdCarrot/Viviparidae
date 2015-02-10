#! /usr/bin/env python
import os
import sys
import time
import random
import string
import traceback
import threading
from threading import Timer, Semaphore
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from watchdog.events import FileSystemEventHandler
from git import Repo


_git_semaphore = Semaphore(1)

def use_git(func):
  def check_semaphore(self=None, *args, **kwargs):
    _git_semaphore.acquire()
    result = None
    try:
      if self:
        result = func(self, *args, **kwargs)
      else:
        result = func(*args, **kwargs)
    except:
      print traceback.format_exc()
    _git_semaphore.release()
    return result
  return check_semaphore


class GitFileChecker(PatternMatchingEventHandler):

  def __init__(self, repo=None, branch_name='_viviparidea', check_interval=1, ignore_directories=False):
    super(GitFileChecker, self).__init__()
    self._ignore_directories = ignore_directories
    self._check_interval = check_interval
    self._events = dict()
    self._branch_name = branch_name
    self._vivi_branch = None
        
    self._ignore_patterns = ['.', './', './.git', './.git/*']
    try:
      with open('.gitignore')  as ignore_file:
        for line in ignore_file.read().splitlines():
          if not line.startswith('./') or not line.startswith('*'):
            line = './' + line
          if os.path.isdir(line):
            self._ignore_patterns.append(line + '/*')
          self._ignore_patterns.append(line)
        print 'Ignore these patterns:'
        print '\t'.join(self._ignore_patterns), '\n'
    except:
      pass

    self._repo = Repo('.') if repo is None else repo

    self._files = [file_name for file_name, v in self._repo.index.entries.keys()]
    print 'Follow these files:'
    print '\t'.join(self._files), '\n'

  def make_new_branch(self):
    try:
      return self._repo.create_head(self._branch_name)
    except OSError:
      self._branch_name = self._branch_name + '_new'
      return self.make_new_branch()

  @use_git
  def reset_vivi_branch(self):
    self._repo.delete_head([self._vivi_branch], force=True)
    self._vivi_branch = None

  def on_any_event(self, event):
    """
    event.event_type
      'modified' | 'created' | 'moved' | 'deleted'
    event.is_directory
      True | False
    event.src_path
      path/to/observed/file
    """
    if event.src_path.startswith('./'):
      event._src_path = event.src_path[2:]
    self._events[event.src_path] = event
    def _event_checker(src_path):
      try:
        event = self._events[src_path]
        if event.event_type == 'modified':
          if event.src_path not in self._files:
            event.event_type = 'created'
            self._files.append(event.src_path)
          elif event.is_directory:
            return
        elif event.event_type == 'created':
            self._files.append(event.src_path)
      except Exception, e:
        pass
      try:
        self.commit()
      except:
        print 'Failed to commit'
        print traceback.format_exc()
    
    Timer(self._check_interval, _event_checker, args=[event.src_path]).start()

  @use_git
  def commit(self):
    if len(self._events) == 0:
      return
    add_files = []
    removed_files = []
    commit_msg = ''
    keys = self._events.keys()
    for key in keys:
      event = self._events.pop(key)
      if event.event_type == 'deleted' and event.src_path in self._files:
        removed_files.append(event.src_path)
        self._files.remove(event.src_path)
        commit_msg = commit_msg + str(event.event_type) + ': ' + event.src_path + '\n'
      elif os.path.exists(event.src_path):
        if event.src_path not in self._files:
          self._files.append(event.src_path)
        add_files.append(event.src_path)
        commit_msg = commit_msg + str(event.event_type) + ': ' + event.src_path + '\n'
    if len(commit_msg) == 0:
      return
    
    last_commit = self._repo.head.commit
    if len(add_files) > 0:
      self._repo.index.add(add_files)
    if len(removed_files) > 0:
      self._repo.index.remove(removed_files)

    if self._vivi_branch is None:
      self._vivi_branch = self.make_new_branch()
    else:
      original_branch = self._repo.head.reference
      self._repo.head.reference = self._vivi_branch
    
      if len(add_files) > 0:
        self._repo.index.add(add_files)
      if len(removed_files) > 0:
        self._repo.index.remove(removed_files)

      self._repo.index.commit(commit_msg)
      self._repo.head.reference = original_branch

    print self._vivi_branch.commit.name_rev
    print commit_msg


class GitCommitChecker(FileSystemEventHandler):
  def __init__(self, git_handler, repo=None):
    super(GitCommitChecker, self).__init__()
    self._git_handler = git_handler
    self._repo = Repo('.') if repo is None else repo
    self._events = []
    self._last_commits = dict()
    for head in repo.heads:
      self._last_commits[head.name] = head.commit.name_rev

  @use_git
  def _event_checker(self):
    if len(self._events) == 0:
      return
    self._events = []
    for head in repo.heads:
      if head.name == self._git_handler._branch_name:
        pass
      elif self._last_commits[head.name] != head.commit.name_rev:
        self._last_commits[head.name] = head.commit.name_rev
        self._git_handler.reset_vivi_branch()
        return

  def on_any_event(self, event):
    self._events.append(event)
    Timer(self._git_handler._check_interval, self._event_checker).start()


if __name__ == "__main__":
  path = sys.argv[1] if len(sys.argv) > 1 else '.'

  repo = Repo(path)

  file_checker = GitFileChecker(repo=repo) 
  file_observer = Observer()
  file_observer.schedule(file_checker, path, recursive=True)
  file_observer.start()

  git_checker = GitCommitChecker(file_checker, repo=repo)  
  git_observer = Observer()
  git_observer.schedule(git_checker, os.path.join(path, '.git'), recursive=True)
  git_observer.start()

  try:
    while True:
      time.sleep(1)
  except:
    file_observer.stop()
    git_observer.stop()

  file_observer.join()
  git_observer.join()
