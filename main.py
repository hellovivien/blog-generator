import pandas as pd
from datetime import datetime
from db import Database
import streamlit as st
from fake_useragent import UserAgent
import people_also_ask as paa # local custom version to force english results
import requests
import json
from fastapi.encoders import jsonable_encoder
from math import ceil
import random
import transformers
from tinydb import where
import time
import re


DB_PATH = 'db.json'
STREAMLIT_OUT = True # set False for console output



# func for display

def write(input, st_func=None):
    if STREAMLIT_OUT:
        if st_func:
            st_func(input)
        else:
            st.markdown(input)
    else:
        print(input)

def task_completed():
    write('**task completed!**', st_func=st.success)

def create_menu():
    first_item = 'create a blog'
    if not 'menu_value' in st.session_state:
        st.session_state.menu_value = first_item
    menu = [first_item]
    with Database() as db:
        all_blogs = db.table('blogs').all()
    if len(all_blogs) > 0:
        menu += [blog['search'] for blog in all_blogs]
    return menu    


# func for text cleaning


def remove_html_tags(content):
    '''
    remove html
    '''      
    p = re.compile(r'<.*?>')
    return p.sub('', content)

def end_with_dot(content):
    '''
    cut the text from 0 to last sentence dot
    '''    
    match = None
    for match in re.finditer("([a-z]\. )",content):
        pass
    if match is None:
        end_of_article = len(content)
    else:
        end_of_article = match.span()[0]+2
    return content[0:end_of_article]

def fix_question(question):
    '''
    remove text after question e.g. Rechercher: .....
    '''
    end = question.index('?')
    return question[0:end+1]    
         

def generate_blog(search):
    blog = Blog(search)
    with Database() as db:
        blog_json = db.table('blogs').get(where('search') == search)
        if blog_json:
            write('Blog found! skip paa', st_func=st.info)
            blog_json['articles'] = [] # reset articles
            blog.load_json(blog_json)
            generator = BlogGenerator(blog)
            generator.generate_articles()
            db.table('blogs').update(jsonable_encoder(generator.blog), where('search') == search)
            write('**Blog updated!**', st_func=st.success)
        else:
            blog = Blog(search)
            generator = BlogGenerator(blog)
            generator.pipeline()             

def main():
    st.set_page_config(layout="wide")
    # create menu
    menu = create_menu()
    menu_choice = st.sidebar.radio('Menu', options=menu, index=menu.index(st.session_state.menu_value))
    # create a new blog if search input is new or generate new articles if already exists
    if menu_choice == 'create a blog':        
        st.header('Create your blog')
        with st.form(key="create_blog"):
            search = st.text_input('search', 'tesla', key='search')
            if st.form_submit_button('create blog'):
                generate_blog(search)
    # display blogs
    else:
        with Database() as db:
            blog = db.table('blogs').get(where('search') == menu_choice)
            if blog:
                for article in blog['articles']:
                    st.header(article['title'])
                    st.markdown(article['content'])
                    st.write('<hr>', unsafe_allow_html=True)


class Blog():

    def __init__(self, search):
        self.search = search
        self.created_at = datetime.now()
        self.keywords = []
        self.related_questions = []
        self.articles = []

    def load_json(self, json):
        self.__dict__.update(json)         

    def save(self):
        with Database() as db:
            db.table('blogs').insert(jsonable_encoder(self))
        return True        


class BlogGenerator():

    query_url = 'https://suggestqueries.google.com/complete/search?output=chrome&hl=en&gl=us&q='

    def __init__(self, blog, min_articles=4, max_length=500):
        self.blog = blog
        self.min_articles = min_articles
        self.max_length = max_length

    def get_keywords(self):
        ua = UserAgent()
        headers = {"user-agent": ua.chrome}
        url = self.query_url+self.blog.search
        response = requests.get(url, headers=headers, verify=False)
        suggestions = json.loads(response.text)
        self.blog.keywords = suggestions[1]
        write('**keywords**: {}'.format(', '.join(self.blog.keywords)), st_func=st.info)
        return len(self.blog.keywords) > 0 # task complete
                   
    def get_questions(self):
        for keyword in self.blog.keywords:
            questions_asked = paa.get_related_questions(keyword)
            if len(questions_asked)>0:
                write('Generate questions for **{}**...'.format(keyword), st_func=st.warning)
                for i,question in enumerate(questions_asked):
                    question = fix_question(question)
                    if question not in self.blog.related_questions: # avoid question duplicate
                        write('{}. *{}*'.format(i+1, question), st_func=st.info)
                        self.blog.related_questions.append(question)
                        time.sleep(0.5) # avoid google ban        
        return len(self.blog.related_questions) > 0 # task complete

        

    def generate_articles(self):
        '''
        Generate articles from related questions with gpt2
        ''' 
        generator = transformers.pipeline('text-generation', model='gpt2')
        transformers.set_seed(42)
        write('**Generate articles...**', st_func=st.warning)
        titles = self.blog.related_questions
        while(len(self.blog.articles) < self.min_articles and len(titles) > 0): # while dont have enough questions or try all questions
            title = titles.pop(random.randint(0, len(titles)-1)) # pick random question
            content = generator(title, max_length=self.max_length, num_return_sequences=2) # text generation
            content = content[0]['generated_text'][len(title):] # cut question from content
            content = remove_html_tags(content)
            content = end_with_dot(content)
            if len(content) > 150: # check size after cleaning 
                self.blog.articles.append({
                    'title':title,
                    'content':content
                })
                write('new article : *{}*'.format(title), st_func=st.info)
        return len(self.blog.articles) > 0 # task complete

    def pipeline(self):
        if self.get_keywords():
            task_completed()
            if self.get_questions():
                task_completed()
                if self.generate_articles():
                    task_completed()
                    if self.blog.save():
                        write('**Blog saved!**', st_func=st.success)
                        st.session_state.menu_value = self.blog.search
                        time.sleep(1)
                        st.experimental_rerun()
                        return True
        return False    

if __name__ == '__main__':
    main()