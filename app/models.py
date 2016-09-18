# -*- coding: utf-8 -*-

from app import db
from .taggers import StanfordTagger
AQUSATagger = StanfordTagger()
#from nltk.metrics import distance

import re
import nltk
import nltk.metrics.distance
import pandas
import operator
from collections import Counter
# Classes: Story, Error, Project  

class Story(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  text = db.Column(db.Text)
  role = db.Column(db.Text)
  means = db.Column(db.Text)
  ends = db.Column(db.Text)
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
  errors = db.relationship('Error', backref='story', lazy='dynamic', cascade='save-update, merge, delete')

  def __repr__(self):
    return '<story: %r, text=%s>' % (self.id, self.text)

  def serialize(self):
    class_dict = self.__dict__
    del class_dict['_sa_instance_state']
    return class_dict

  def create(text, project_id, analyze=False):
    story = Story(text=text, project_id=project_id)
    db.session.add(story)
    db.session.commit()
    db.session.merge(story)
    story.chunk()
    if analyze: story.analyze()
    return story

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def delete(self):
    db.session.delete(self)
    db.session.commit()

  def chunk(self):
    StoryChunker.chunk_story(self)
    return self

  def re_chunk(self):
    self.role = None
    self.means = None
    self.ends = None
    StoryChunker.chunk_story(self)
    return self

  def analyze(self):
    WellFormedAnalyzer.well_formed(self)
    Analyzer.atomic(self)
    Analyzer.unique(self, True)
    MinimalAnalyzer.minimal(self)
    Analyzer.uniform(self)
    self.remove_duplicates_of_false_positives()
    return self

  def re_analyze(self):
    for error in Error.query.filter_by(story=self, false_positive=False).all():
      error.delete()
    self.analyze()
    return self

  def remove_duplicates_of_false_positives(self):
    for false_positive in self.errors.filter_by(false_positive=True):
      duplicates = Error.query.filter_by(story=self, kind=false_positive.kind, subkind=false_positive.subkind, false_positive=False).all()
      if duplicates:
        for duplicate in duplicates:
          duplicate.delete()
      else:
        false_positive.delete()
    return self

class Criteria(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  text = db.Column(db.Text)
  given = db.Column(db.Text)
  when = db.Column(db.Text)
  then = db.Column(db.Text)
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
  # errors = db.relationship('Error', backref='story', lazy='dynamic', cascade='save-update, merge, delete')

  def __repr__(self):
    return '<criteria: %r, text=%s>' % (self.id, self.text)

  def serialize(self):
    class_dict = self.__dict__
    del class_dict['_sa_instance_state']
    return class_dict

  def create(text, project_id, analyze=False):
    criteria = Criteria(text=text, project_id=project_id)
    db.session.add(criteria)
    db.session.commit()
    db.session.merge(criteria)
    criteria.chunk()
    if analyze: criteria.analyze()
    return criteria

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def delete(self):
    db.session.delete(self)
    db.session.commit()

  def chunk(self):
    CriteriaChunker.chunk_criteria(self)
    return self

  def re_chunk(self):
    self.given = None
    self.when = None
    self.then = None
    CriteriaChunker.chunk_criteria(self)
    return self

  def analyze(self):
    WellFormedAnalyzer.well_formed(self)
    Analyzer.atomic(self)
    Analyzer.unique(self, True)
    MinimalAnalyzer.minimal(self)
    #Analyzer.uniform(self)
    self.remove_duplicates_of_false_positives()
    return self

  def re_analyze(self):
    for error in Error.query.filter_by(story=self, false_positive=False).all():
      error.delete()
    self.analyze()
    return self

  def remove_duplicates_of_false_positives(self):
    for false_positive in self.errors.filter_by(false_positive=True):
      duplicates = Error.query.filter_by(criteria=self, kind=false_positive.kind, subkind=false_positive.subkind, false_positive=False).all()
      if duplicates:
        for duplicate in duplicates:
          duplicate.delete()
      else:
        false_positive.delete()
    return self

class Title(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  text = db.Column(db.Text)
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
  errors = db.relationship('ErrorTitle', backref='title', lazy='dynamic', cascade='save-update, merge, delete')

  def __repr__(self):
    return '<title: %r, text=%s>' % (self.id, self.text)

  def serialize(self):
    class_dict = self.__dict__
    del class_dict['_sa_instance_state']
    return class_dict

  def create(text, project_id, analyze=False):
    title = Title(text=text, project_id=project_id)
    db.session.add(title)
    db.session.commit()
    db.session.merge(title)
    if analyze: title.analyze()
    return title

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def delete(self):
    db.session.delete(self)
    db.session.commit()

  def analyze(self):
    WellFormedAnalyzer.well_formed(self)
    Analyzer.atomic(self)
    Analyzer.unique(self, True)
    MinimalAnalyzer.minimal(self)
    #Analyzer.uniform(self)
    self.remove_duplicates_of_false_positives()
    return self

  def re_analyze(self):
    for error in ErrorTitle.query.filter_by(title=self, false_positive=False).all():
      error.delete()
    self.analyze()
    return self

  def remove_duplicates_of_false_positives(self):
    for false_positive in self.errors.filter_by(false_positive=True):
      duplicates = ErrorTitle.query.filter_by(title=self, kind=false_positive.kind, subkind=false_positive.subkind, false_positive=False).all()
      if duplicates:
        for duplicate in duplicates:
          duplicate.delete()
      else:
        false_positive.delete()
    return self


class Project(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(120), index=True, nullable=False)
  format = db.Column(db.Text, nullable=True, default="As a,I'm able to,So that")
  stories = db.relationship('Story', backref='project', lazy='dynamic', cascade='save-update, merge, delete')
  criterias = db.relationship('Criteria', backref='project', lazy='dynamic', cascade='save-update, merge, delete')
  titles = db.relationship('Title', backref='project', lazy='dynamic', cascade='save-update, merge, delete')
  errors = db.relationship('Error', backref='project', lazy='dynamic')

  def __repr__(self):
    return '<Project: %r, name=%s>' % (self.id, self.name)

  def serialize(self):
    class_dict = self.__dict__
    del class_dict['_sa_instance_state']
    return class_dict

  def create(name):
    project = Project(name=name)
    db.session.add(project)
    db.session.commit()
    db.session.merge(project)
    return project

  def delete(self):
    db.session.delete(self)
    db.session.commit() 

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def process_csv(self, path):
    items = pandas.read_csv(path, header=-1)
    for story in items[0]:
      Story.create(text=story, project_id=self.id)
    for criteria in items[1]:
      Criteria.create(text=criteria, project_id=self.id)
    for title in items[2]:
      Title.create(title, self.id)
    self.analyze()
    return None

  def get_common_format(self):
    most_common_format = []
    for chunk in ['role', 'means', 'ends']:
      chunks = [Analyzer.extract_indicator_phrases(getattr(story,chunk), chunk) for story in self.stories]
      chunks = list(filter(None, chunks))
      try:
        most_common_format += [Counter(chunks).most_common(1)[0][0].strip()]
      except:
        print('')
    self.format = ', '.join(most_common_format)
    self.save()
    return "New format is: " + self.format

  def analyze(self):
    self.get_common_format()
    for story in self.stories.all():
      story.re_chunk()
      story.re_analyze()
    return self

class Error(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  highlight = db.Column(db.Text, nullable=False)
  kind = db.Column(db.String(120), index=True,  nullable=False)
  subkind = db.Column(db.String(120), nullable=False)
  severity = db.Column(db.String(120), nullable=False)
  false_positive = db.Column(db.Boolean, default=False, nullable=False)
  story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

  def __repr__(self):
    return '<Error: %s, highlight=%s, kind=%s>' % (self.id, self.highlight, self.kind)

  def create(highlight, kind, subkind, severity, story):
    error = Error(highlight=highlight, kind=kind, subkind=subkind, severity=severity, story_id=story.id, project_id=story.project.id)
    db.session.add(error)
    db.session.commit()
    db.session.merge(error)
    return error

  def delete(self):
    db.session.delete(self)
    db.session.commit()

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def create_unless_duplicate(highlight, kind, subkind, severity, story):
    error = Error(highlight=highlight, kind=kind, subkind=subkind, severity=severity, story_id=story.id, project_id=story.project.id)
    duplicates = Error.query.filter_by(highlight=highlight, kind=kind, subkind=subkind,
      severity=severity, story_id=story.id, project_id=story.project.id, false_positive=False).all()
    if duplicates:
      return 'duplicate'
    else:
      db.session.add(error)
      db.session.commit()
      db.session.merge(error)
      return error

  def correct_minor_issue(self):
    story = self.story
    CorrectError.correct_minor_issue(self)
    return story

class ErrorCriteria(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  highlight = db.Column(db.Text, nullable=False)
  kind = db.Column(db.String(120), index=True,  nullable=False)
  subkind = db.Column(db.String(120), nullable=False)
  severity = db.Column(db.String(120), nullable=False)
  false_positive = db.Column(db.Boolean, default=False, nullable=False)
  criteria_id = db.Column(db.Integer, db.ForeignKey('criteria.id'), nullable=False)
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

  def __repr__(self):
    return '<Error: %s, highlight=%s, kind=%s>' % (self.id, self.highlight, self.kind)

  def create(highlight, kind, subkind, severity, criteria):
    error = ErrorCriteria(highlight=highlight, kind=kind, subkind=subkind, severity=severity, criteria_id=criteria.id, project_id=criteria.project.id)
    db.session.add(error)
    db.session.commit()
    db.session.merge(error)
    return error

  def delete(self):
    db.session.delete(self)
    db.session.commit()

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def create_unless_duplicate(highlight, kind, subkind, severity, criteria):
    error = ErrorCriteria(highlight=highlight, kind=kind, subkind=subkind, severity=severity, criteria_id=criteria.id, project_id=criteria.project.id)
    duplicates = ErrorCriteria.query.filter_by(highlight=highlight, kind=kind, subkind=subkind,
      severity=severity, criteria_id=criteria.id, project_id=criteria.project.id, false_positive=False).all()
    if duplicates:
      return 'duplicate'
    else:
      db.session.add(error)
      db.session.commit()
      db.session.merge(error)
      return error

  def correct_minor_issue(self):
    criteria = self.criteria
    CorrectError.correct_minor_issue(self)
    return criteria

class ErrorTitle(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  highlight = db.Column(db.Text, nullable=False)
  kind = db.Column(db.String(120), index=True,  nullable=False)
  subkind = db.Column(db.String(120), nullable=False)
  severity = db.Column(db.String(120), nullable=False)
  false_positive = db.Column(db.Boolean, default=False, nullable=False)
  title_id = db.Column(db.Integer, db.ForeignKey('title.id'), nullable=False)
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

  def __repr__(self):
    return '<Error: %s, highlight=%s, kind=%s>' % (self.id, self.highlight, self.kind)

  def create(highlight, kind, subkind, severity, title):
    error = ErrorCriteria(highlight=highlight, kind=kind, subkind=subkind, severity=severity, title_id=title.id, project_id=title.project.id)
    db.session.add(error)
    db.session.commit()
    db.session.merge(error)
    return error

  def delete(self):
    db.session.delete(self)
    db.session.commit()

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def create_unless_duplicate(highlight, kind, subkind, severity, title):
    error = ErrorCriteria(highlight=highlight, kind=kind, subkind=subkind, severity=severity, title_id=title.id, project_id=title.project.id)
    duplicates = ErrorTitle.query.filter_by(highlight=highlight, kind=kind, subkind=subkind,
      severity=severity, title_id=title.id, project_id=title.project.id, false_positive=False).all()
    if duplicates:
      return 'duplicate'
    else:
      db.session.add(error)
      db.session.commit()
      db.session.merge(error)
      return error

  def correct_minor_issue(self):
    title = self.title
    CorrectErrorTitle.correct_minor_issue(self)
    return title

# ACCEPTANCE CRITERIA
GIVEN_INDICATORS = ["^Given that", "^Given this", "^Given the", "^Given"]
WHENS_INDICATORS = ["When the", "When"]
THENS_INDICATORS = ["Then the", "Then"]

# STORY
ROLE_INDICATORS = ["^As an ", "^As a ", "^As "]
MEANS_INDICATORS = ["I'm able to ", "I am able to ", "I want to ", "I wish to ", "I can "]
ENDS_INDICATORS = ["So that ", "In order to ", "So "]
CONJUNCTIONS = [' and ', '&', '+', ' or ']
PUNCTUATION = ['.', ';', ':', '‒', '–', '—', '―', '‐', '-', '?', '*']
BRACKETS = [['(', ')'], ['[', ']'], ['{', '}'], ['⟨', '⟩']]
ERROR_KINDS = { 'well_formed_content': [
                  { 'subkind': 'means', 'rule': 'Analyzer.well_formed_content_rule(story.means, "means", ["means"])', 'severity':'medium', 'highlight':'str("Make sure the means includes a verb and a noun. Our analysis shows the means currently includes: ") + Analyzer.well_formed_content_highlight(story.means, "means")'},
                  { 'subkind': 'role', 'rule': 'Analyzer.well_formed_content_rule(story.role, "role", ["NP"])', 'severity':'medium', 'highlight':'str("Make sure the role includes a person noun. Our analysis shows the role currently includes: ") + Analyzer.well_formed_content_highlight(story.role, "role")'},
                ],

                'atomic': [
                  { 'subkind':'conjunctions', 'rule':"Analyzer.atomic_rule(getattr(story,chunk), chunk)", 'severity':'high', 'highlight':"Analyzer.highlight_text(story, CONJUNCTIONS, 'high')"}
                ],
                'unique': [
                  { 'subkind':'identical', 'rule':"Analyzer.identical_rule(story, cascade)", 'severity':'high', 'highlight':'str("Remove all duplicate user stories")' }
                ],
                'uniform': [
                  { 'subkind':'uniform', 'rule':"Analyzer.uniform_rule(story)", 'severity':'medium', 'highlight':'"Use the most common template: %s" % story.project.format'}
                ],

              }
CHUNK_GRAMMAR = """
      NP: {<DT|JJ|NN.*>}
      NNP: {<NNP.*>}
      AP: {<RB.*|JJ.*>}
      VP: {<VB.*><NP>*}
      MEANS: {<AP>?<VP>}
      ENDS: {<AP>?<VP>}
    """

class Analyzer:
  def atomic(story):
    for chunk in ['"role"', '"means"', '"ends"']:
      Analyzer.generate_errors('atomic', story, chunk=chunk)
    return story

  def unique(story, cascade):
    Analyzer.generate_errors('unique', story, cascade=cascade)
    return story

  def uniform(story):
    Analyzer.generate_errors('uniform', story)
    return story
      
  def detect_indicator_phrases(text):
    indicator_phrases = {'role': False, 'means': False, 'ends': False}
    for key in indicator_phrases:
      for indicator_phrase in eval(key.upper() + '_INDICATORS'):
        if indicator_phrase.lower() in text.lower(): indicator_phrases[key] = True
    return indicator_phrases

  def generate_errors(kind, story, **kwargs):
    for kwarg in kwargs:
      exec(kwarg+'='+ str(kwargs[kwarg]))
    for error_type in ERROR_KINDS[kind]:
      if eval(error_type['rule']):
        Error.create_unless_duplicate(eval(error_type['highlight']), kind, error_type['subkind'], error_type['severity'], story)

  def inject_text(text, severity='medium'):
    return "<span class='highlight-text severity-" + severity + "'>%s</span>" % text

  def atomic_rule(chunk, kind):
    sentences_invalid = []
    if chunk: 
      for x in CONJUNCTIONS:
        if x in chunk.lower():
          if kind == 'means':
            for means in chunk.split(x):
              sentences_invalid.append(Analyzer.well_formed_content_rule(means, 'means', ['MEANS']))
          if kind == 'role':
            for role in chunk.split(x):
              sentences_invalid.append(Analyzer.well_formed_content_rule(role, "role", ["NP"]))
          if kind == 'event':
            for means in chunk.split(x):
              sentences_invalid.append(Analyzer.well_formed_content_rule(means, 'whens', ['WHENS']))
    return sentences_invalid.count(False) > 1

  def identical_rule(story, cascade):
    identical_stories = Story.query.filter((Story.text==story.text) & (Story.project_id == int(story.project_id))).all()
    identical_stories.remove(story)
    if cascade:
      for story in identical_stories:
        for error in story.errors.filter(Error.kind=='unique').all(): error.delete()
        Analyzer.unique(story, False)
    return (True if identical_stories else False)

  def highlight_text(story, word_array, severity):
    highlighted_text = story.text
    indices = []
    for word in word_array:
      if word in story.text.lower(): indices += [ [story.text.index(word), word] ]
    indices.sort(reverse=True)
    for index, word in indices:
      highlighted_text = highlighted_text[:index] + "<span class='highlight-text severity-" + severity + "'>" + word + "</span>" + highlighted_text[index+len(word):]
    return highlighted_text

  def well_formed_content_rule(story_part, kind, tags):
    result = Analyzer.content_chunk(story_part, kind)
    well_formed = True
    for tag in tags:
      for x in result.subtrees():
        if tag.upper() in x.label(): well_formed = False
    return well_formed

  def uniform_rule(story):
     project_format = story.project.format.split(',')
     chunks = []
     for chunk in ['role', 'means', 'ends']:
       chunks += [Analyzer.extract_indicator_phrases(getattr(story,chunk), chunk)]
     chunks = list(filter(None, chunks))
     chunks = [c.strip() for c in chunks]
     result = False
     if len(chunks) == 1: result = True
     for x in range(0,len(chunks)):
       if nltk.metrics.distance.edit_distance(chunks[x].lower(), project_format[x].lower()) > 3:
         result = True
     return result

  def well_formed_content_highlight(story_part, kind):
    return str(Analyzer.content_chunk(story_part, kind))

  def content_chunk(chunk, kind):
    sentence = AQUSATagger.parse(chunk)[0]
    sentence = Analyzer.strip_indicators_pos(chunk, sentence, kind)
    cp = nltk.RegexpParser(CHUNK_GRAMMAR)
    result = cp.parse(sentence)
    return result

  def extract_indicator_phrases(text, indicator_type):
    if text:
      indicator_phrase = []
      for indicator in eval(indicator_type.upper() + '_INDICATORS'):
        if re.compile('(%s)' % indicator.lower()).search(text.lower()): indicator_phrase += [indicator.replace('^', '')]
      return max(indicator_phrase, key=len) if indicator_phrase else None
    else:
      return text

  def strip_indicators_pos(text, pos_text, indicator_type):
    for indicator in eval(indicator_type.upper() + '_INDICATORS'):
      if indicator.lower().strip() in text.lower():
        indicator_words = nltk.word_tokenize(indicator)
        pos_text = [x for x in pos_text if x[0] not in indicator_words]
    return pos_text


class WellFormedAnalyzer:
  def well_formed(story):
    WellFormedAnalyzer.means(story)
    WellFormedAnalyzer.role(story)
    WellFormedAnalyzer.means_comma(story)
    WellFormedAnalyzer.ends_comma(story)
    return story

  def means(story):
    if not story.means:
      Error.create_unless_duplicate('Add a means', 'well_formed', 'no_means', 'high', story )
    return story

  def role(story):
    if not story.role:
      Error.create_unless_duplicate('Add a role', 'well_formed', 'no_role', 'high', story )
    return story

  def means_comma(story):
    if story.role is not None and story.means is not None:
      if story.role.count(',') == 0:
        highlight = story.role + Analyzer.inject_text(',') + ' ' + story.means
        Error.create_unless_duplicate(highlight, 'well_formed', 'no_means_comma', 'minor', story )
    return story

  def ends_comma(story):
    if story.means is not None and story.ends is not None:
      if story.means.count(',') == 0:
        highlight = story.means + Analyzer.inject_text(',') + ' ' + story.ends
        Error.create_unless_duplicate(highlight, 'well_formed', 'no_ends_comma', 'minor', story )
    return story

class MinimalAnalyzer:
  def minimal(story):
    MinimalAnalyzer.punctuation(story)
    MinimalAnalyzer.brackets(story)
    return story

  def punctuation(story):
    if any(re.compile('(\%s .)' % x).search(story.text.lower()) for x in PUNCTUATION):
      highlight = MinimalAnalyzer.punctuation_highlight(story, 'high')
      Error.create_unless_duplicate(highlight, 'minimal', 'punctuation', 'high', story )
    return story

  def punctuation_highlight(story, severity):
    highlighted_text = story.text
    indices = []
    for word in PUNCTUATION:
      if re.search('(\%s .)' % word, story.text.lower()): indices += [ [story.text.index(word), word] ]
    first_punct = min(indices)
    highlighted_text = highlighted_text[:first_punct[0]] + "<span class='highlight-text severity-" + severity + "'>" + highlighted_text[first_punct[0]:] + "</span>"
    return highlighted_text

  def brackets(story):
    if any(re.compile('(\%s' % x[0] + '.*\%s(\W|\Z))' % x[1]).search(story.text.lower()) for x in BRACKETS):
      highlight = MinimalAnalyzer.brackets_highlight(story, 'high')
      Error.create_unless_duplicate(highlight, 'minimal', 'brackets', 'high', story )
    return story.errors.all()

  def brackets_highlight(story, severity):
    highlighted_text = story.text
    matches = []
    for x in BRACKETS:
      split_string = '[^\%s' % x[1] + ']+\%s' % x[1]
      strings = re.findall(split_string, story.text)
      match_string = '(\%s' % x[0] + '.*\%s(\W|\Z))' % x[1]
      string_length = 0
      for string in strings:
        result = re.compile(match_string).search(string.lower())
        if result:
          span = tuple(map(operator.add, result.span(), (string_length, string_length)))
          matches += [ [span, result.group()] ]
        string_length += len(string)
    matches.sort(reverse=True)
    for index, word in matches:
      highlighted_text = highlighted_text[:index[0]] + "<span class='highlight-text severity-" +  severity + "'>" + word + "</span>" + highlighted_text[index[1]:]
    return highlighted_text


# TitleChunker and CriteriaChunker need more work
class CriteriaChunker:
  def chunk_criteria(criteria):
    CriteriaChunker.chunk_on_indicators(criteria)
    if criteria.given is None:
      potential_whens = criteria.text
      if criteria.when is not None:
        potential_means = potential_whens.replace(criteria.when, "", 1).strip()
      if criteria.then is not None:
        potential_means = potential_means.replace(criteria.then, "", 1).strip()
      #CriteriaChunker.means_tags_present(criteria, potential_means)
    return criteria.given, criteria.when, criteria.then

  def detect_indicators(criteria):
    indicators = {'given': None, "whens": None, 'thens': None}
    for indicator in indicators:
      indicator_phrase = CriteriaChunker.detect_indicator_phrase(criteria.text.strip(), indicator)
      if indicator_phrase[0]:
        indicators[indicator.lower()] = criteria.text.lower().index(indicator_phrase[1].lower())
    return indicators

  def detect_indicator_phrase(text, indicator_type):
    result = False
    detected_indicators = ['']
    for indicator_phrase in eval(indicator_type.upper() + '_INDICATORS'):
      if re.compile('(%s)' % indicator_phrase.lower()).search(text.lower()):
        result = True
        detected_indicators.append(indicator_phrase.replace('^', ''))
    return (result, max(detected_indicators, key=len))

  def chunk_on_indicators(criteria):
    indicators = CriteriaChunker.detect_indicators(criteria)
    if indicators['whens'] is not None and indicators['thens'] is not None:
      pass
      # indicators = StoryChunker.correct_erroneous_indicators(criteria, indicators)  # Fix here to correct the erroneous
    if indicators['given'] is not None and indicators['whens'] is not None:
      criteria.given = criteria.text[indicators['given']:indicators['whens']].strip()
      criteria.when = criteria.text[indicators['whens']:indicators['thens']].strip()
    elif indicators['given'] is not None and indicators['whens'] is None:
      given = CriteriaChunker.detect_indicator_phrase(criteria.text, 'given')
      new_text = criteria.text.replace(given[1], '')
      sentence = Analyzer.content_chunk(new_text, 'given')
      NPs_after_given = CriteriaChunker.keep_if_NP(sentence)
      if NPs_after_given:
        criteria.given = criteria.text[indicators['given']:(len(given[1]) + len(NPs_after_given))].strip()
    if indicators['thens']:
      criteria.then = criteria.text[indicators['thens']:None].strip()
    criteria.save()
    return criteria

  def keep_if_NP(parsed_tree):
    return_string = []
    for leaf in parsed_tree:
      if type(leaf) is not tuple:
        if leaf[0][0] == 'I':
          break
        elif leaf.label() == 'NP':
          return_string.append(leaf[0][0])
        else:
          break
      elif leaf == (',', ','): return_string.append(',')
    return ' '.join(return_string)

  def means_tags_present(criteria, string):
    if not Analyzer.well_formed_content_rule(string, 'whens', ['WHENS']):
      criteria.whens = string
      criteria.save
    return criteria

  def correct_erroneous_indicators(criteria, indicators):
    # means is larger than ends
    if indicators['whens'] > indicators['thens']:
      new_means = CriteriaChunker.detect_indicator_phrase(criteria.text[:indicators['thens']], 'whens')
      #replication of #427 - refactor?
      if new_means[0]:
        indicators['thens'] = criteria.text.lower().index(new_means[1].lower())
      else:
        indicators['thens'] = None
    return indicators

class StoryChunker:
  def chunk_story(story):
    StoryChunker.chunk_on_indicators(story)
    if story.means is None:
      potential_means = story.text
      if story.role is not None:
        potential_means = potential_means.replace(story.role, "", 1).strip()
      if story.ends is not None:
        potential_means = potential_means.replace(story.ends, "", 1).strip()
      StoryChunker.means_tags_present(story, potential_means)
    return story.role, story.means, story.ends

  def detect_indicators(story):
    indicators = {'role': None, "means": None, 'ends': None}
    for indicator in indicators:
      indicator_phrase = StoryChunker.detect_indicator_phrase(story.text, indicator)
      if indicator_phrase[0]:
        indicators[indicator.lower()] = story.text.lower().index(indicator_phrase[1].lower())
    return indicators

  def detect_indicator_phrase(text, indicator_type):
    result = False
    detected_indicators = ['']
    for indicator_phrase in eval(indicator_type.upper() + '_INDICATORS'):
      if re.compile('(%s)' % indicator_phrase.lower()).search(text.lower()): 
        result = True
        detected_indicators.append(indicator_phrase.replace('^', ''))
    return (result, max(detected_indicators, key=len))

  def chunk_on_indicators(story):
    indicators = StoryChunker.detect_indicators(story)
    if indicators['means'] is not None and indicators['ends'] is not None:
      indicators = StoryChunker.correct_erroneous_indicators(story, indicators)
    if indicators['role'] is not None and indicators['means'] is not None:
      story.role = story.text[indicators['role']:indicators['means']].strip()
      story.means = story.text[indicators['means']:indicators['ends']].strip()
    elif indicators['role'] is not None and indicators['means'] is None:
      role = StoryChunker.detect_indicator_phrase(story.text, 'role')
      new_text = story.text.replace(role[1], '')
      sentence = Analyzer.content_chunk(new_text, 'role')
      NPs_after_role = StoryChunker.keep_if_NP(sentence)
      if NPs_after_role:
        story.role = story.text[indicators['role']:(len(role[1]) + len(NPs_after_role))].strip()
    if indicators['ends']: story.ends = story.text[indicators['ends']:None].strip()
    story.save()
    return story

  def keep_if_NP(parsed_tree):
    return_string = []
    for leaf in parsed_tree:
      if type(leaf) is not tuple:
        if leaf[0][0] == 'I':
          break
        elif leaf.label() == 'NP': 
          return_string.append(leaf[0][0])
        else:
          break
      elif leaf == (',', ','): return_string.append(',')
    return ' '.join(return_string)

  def means_tags_present(story, string):
    if not Analyzer.well_formed_content_rule(string, 'means', ['MEANS']):
      story.means = string
      story.save
    return story

  def correct_erroneous_indicators(story, indicators):
    # means is larger than ends
    if indicators['means'] > indicators['ends']:
      new_means = StoryChunker.detect_indicator_phrase(story.text[:indicators['ends']], 'means')
      #replication of #427 - refactor?
      if new_means[0]:
        indicators['means'] = story.text.lower().index(new_means[1].lower())
      else:
        indicators['means'] = None
    return indicators


class CorrectError:
  def correct_minor_issue(error):
    story = error.story
    eval('CorrectError.correct_%s(error)' % error.subkind)
    return story

  def correct_no_means_comma(error):
    story = error.story
    story.text = story.role + ', ' + story.means 
    if story.ends: story.text = story.text + ' ' + story.ends
    story.save()
    return story

  def correct_no_ends_comma(error):
    story = error.story
    story.text = story.means + ', ' + story.ends
    if story.role: story.text = story.role + ' ' + story.text
    story.save()
    return story

class CorrectErrorCriteria:
  def correct_minor_issue(error):
    story = error.story
    eval('CorrectError.correct_%s(error)' % error.subkind)
    return story

  def correct_no_means_comma(error):
    story = error.story
    story.text = story.role + ', ' + story.means
    if story.ends: story.text = story.text + ' ' + story.ends
    story.save()
    return story

  def correct_no_ends_comma(error):
    story = error.story
    story.text = story.means + ', ' + story.ends
    if story.role: story.text = story.role + ' ' + story.text
    story.save()
    return story

class CorrectErrorTitle:
  def correct_minor_issue(errorTitle):
    title = errorTitle.title
    eval('CorrectErrorTitle.correct_%s(error)' % errorTitle.subkind)
    return title

  def correct_no_means_comma(errorTitle):
    title = errorTitle.title
    title.text = title.role + ', ' + title.means
    if title.ends: title.text = title.text + ' ' + title.ends
    title.save()
    return title

  def correct_no_ends_comma(errorTitle):
    title = errorTitle.story
    title.text = title.means + ', ' + title.ends
    if title.role: title.text = title.role + ' ' + title.text
    title.save()
    return title