import sys                  #시스템 윈도우상에서 cmd에서 전달하게하는 명령어 그런용도?
import bs4                  #BeautifulSoup 라이브러리라는 가장 널리 쓰이는 웹 크롤러  html 파싱
import requests             #유명한 http request 라이브러리
import json                 #웹브라우저와 웹서버 사이에 데이터를 교환할떄 쓰임
import hashlib              #해시함수
import re                   #문자열 정규식 표현 소스 작성하기 위해 필요함
import logging as log       # 파이썬 로깅

from abc import ABCMeta, abstractmethod             #추상클래스를 사용하기 위해 abc import
from json import JSONDecodeError                    #json 라이브러리에서 JSONDecodeError생성
from InstagramUser import InstagramUser             #InstagramUser.py에서 InstagramUser 클래스 가져오기
from InstagramPost import InstagramPost             #InstagramPost.py에서 InstagramPost 클래스 가져오기

def get_md5(s):                                     #파이썬은 함수를 정의할떄 def를 씀. get_md5 함수, 인자s 를 만듬.
    m = hashlib.md5()                               #해시함수 hashlib 라이브러리 md5써서 만듬
    m.update(s.encode())
    return m.hexdigest()                            #해시함수된 메세지 다이제스트 출력할수있음 m출력
                                                    #md5 왜쓰냐면 'X-Instagram-GIS'라는 헤더값 계산에 필요
                                                    #'X-Instagram-GIS' 헤더에 data의 hash값이 들어가야함

class HashTagSearch(metaclass=ABCMeta):
    instagram_root = "https://www.instagram.com"

    def __init__(self, ):           #세션을 초기화 세션은 HTTP request 요청할때 쓰인다.클래스의 메소드를 정의할 때는 self를 꼭 명시해하고 그 메소드를 불러올 때 self는 자동으로 전달됩니다.
        """
        This class performs a search on Instagrams hashtag search engine, and extracts posts for that given hashtag.
        There are some limitations, as this does not extract all occurrences of the hash tag.
        Instead, it extracts the most recent uses of the tag.
        """
        super().__init__()
        self.session = requests.session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0'                                  #인스타그램 내부적으로 사용되는 값/서버에서 정상적인 요청이라고 속이기 위해 셋팅
        self.session.cookies.set('ig_pr', '1', domain='www.instagram.com')
        self.session.cookies.set('ig_vh', '959', domain='www.instagram.com')
        self.session.cookies.set('ig_vw', '1034', domain='www.instagram.com')
        self.session.cookies.set('ig_or', 'landscape-primary', domain='www.instagram.com')

    def extract_recent_tag(self, tag):                                           #인스타그램을 상대로 크롤링
        """
        Extracts Instagram posts for a given hashtag
        :param tag: Hashtag to extract
        """

        url_string = "https://www.instagram.com/explore/tags/%s/" % tag                     #가장 초기 URL에 요청을 하고 node를 가져온다.
        response = bs4.BeautifulSoup(self.session.get(url_string).text, "html.parser")      #response가 파싱결과를 가지고있음.
        potential_query_ids = self.get_query_id(response)
        shared_data = self.extract_shared_data(response)

        media = shared_data['entry_data']['TagPage'][0]['graphql']['hashtag']['edge_hashtag_to_media']['edges']

        posts = []
        for node in media:
            post = self.extract_recent_instagram_post(node['node'])
            posts.append(post)
        self.save_results(posts)

        hashtag = shared_data['entry_data']['TagPage'][0]['graphql']['hashtag']         #크롤링 스크롤 시작(인스타그램 내 스크롤 로딩)
        end_cursor = hashtag['edge_hashtag_to_media']['page_info']['end_cursor']

        # figure out valid queryId
        success = False
        for potential_id in potential_query_ids:
            variables = {
                'tag_name': tag,
                'first': 4,
                'after': end_cursor
            }
            url = "https://www.instagram.com/graphql/query/?query_hash=%s&variables=%s" % (
                potential_id, json.dumps(variables).replace(" ", ""))
            try:
                response = self.session.get(url, headers={
                    'X-Instagram-GIS': get_md5(shared_data['rhx_gis'] + ':' + json.dumps(variables).replace(" ", ""))})
                data = response.json()
                if data['status'] == 'fail':
                    # empty response, skip
                    continue
                query_id = potential_id
                success = True
                break
            except JSONDecodeError as de:
                # no valid JSON retured, most likely wrong query_id resulting in 'Oops, an error occurred.'
                pass
        if not success:
            log.error("Error extracting Query Id, exiting")
            sys.exit(1)                                                             #크롤링 스크롤 끝 쿼리정보 추출

        while end_cursor is not None:                                               #추출한 쿼리정보로 계속 요청(스크롤)
            variables = {
                'tag_name': tag,
                'first': 12,
                'after': end_cursor
            }
            url = "https://www.instagram.com/graphql/query/?query_hash=%s&variables=%s" % (
                query_id, json.dumps(variables).replace(" ", ""))
            try:
                response = self.session.get(url, headers={              #스크롤될때 쿼리 정보를 계속 요쳥하기 위해서 필요
                    'X-Instagram-GIS': get_md5(shared_data['rhx_gis'] + ':' + json.dumps(variables).replace(" ", ""))})
                data = response.json()
                if data['status'] == 'fail':
                    print("END")
                    break
            except:
                print("ERROR")
                break

            end_cursor = data['data']['hashtag']['edge_hashtag_to_media']['page_info']['end_cursor']
            posts = []
            for node in data['data']['hashtag']['edge_hashtag_to_media']['edges']:
                posts.append(self.extract_recent_query_instagram_post(node['node']))

            total = self.save_results(posts)

        return total

    @staticmethod
    def extract_shared_data(doc):
        for script_tag in doc.find_all("script"):
            if script_tag.text.startswith("window._sharedData ="):
                shared_data = re.sub("^window\._sharedData = ", "", script_tag.text)
                shared_data = re.sub(";$", "", shared_data)
                shared_data = json.loads(shared_data)
                return shared_data

    @staticmethod
    def extract_recent_instagram_post(node):
        return InstagramPost(
            post_id=node['id'],
            code=node['shortcode'],
            user=InstagramUser(user_id=node['owner']['id']),
            caption=HashTagSearch.extract_caption(node),
            display_src=node['display_url'],
            is_video=node['is_video'],
            created_at=node['taken_at_timestamp']
        )

    @staticmethod
    def extract_recent_query_instagram_post(node):
        return InstagramPost(
            post_id=node['id'],
            code=node['shortcode'],
            user=InstagramUser(user_id=node['owner']['id']),
            caption=HashTagSearch.extract_caption(node),
            display_src=node['display_url'],
            is_video=node['is_video'],
            created_at=node['taken_at_timestamp']
        )

    @staticmethod
    def extract_caption(node):
        if len(node['edge_media_to_caption']['edges']) > 0:
            return node['edge_media_to_caption']['edges'][0]['node']['text']
        else:
            return None

    @staticmethod
    def extract_owner_details(owner):
        """
        Extracts the details of a user object.
        :param owner: Instagrams JSON user object
        :return: An Instagram User object
        """
        username = None
        if "username" in owner:
            username = owner["username"]
        is_private = False
        if "is_private" in owner:
            is_private = is_private
        user = InstagramUser(owner['id'], username=username, is_private=is_private)
        return user

    def get_query_id(self, doc):
        query_ids = []
        for script in doc.find_all("script"):
            if script.has_attr("src"):
                text = requests.get("%s%s" % (self.instagram_root, script['src'])).text
                if "queryId" in text:
                    for query_id in re.findall("(?<=queryId:\")[0-9A-Za-z]+", text):
                        query_ids.append(query_id)
        return query_ids

    @abstractmethod
    def save_results(self, instagram_results):                              #크롤링 된 데이터 저장.
        """
        Implement yourself to work out what to do with each extract batch of posts
        :param instagram_results: A list of Instagram Posts
        """
