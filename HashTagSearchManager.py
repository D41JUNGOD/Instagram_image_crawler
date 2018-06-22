import sqlite3
import os
import cv2
from HashTagSearch import HashTagSearch


class HashTagSearchManager(HashTagSearch):
    def __init__(self, storage_folder='images'):            #이미지를 저장할 images 폴더를 생성
        super().__init__()
        self.storage_path = os.path.join(os.getcwd(), storage_folder)       #현재 작업 디렉토리 위치 + 현재 저장폴더에 생성
        if not os.path.exists(self.storage_path):
            os.mkdir(self.storage_path)

                                                             #db구조를 초기화 시킨다. (15~38)
        self.conn = sqlite3.connect("database.sqlite3")
        self.cur = self.conn.cursor()
        self.cur.execute("""CREATE TABLE IF NOT EXISTS Post (
                            id VARCHAR(256) PRIMARY KEY, 
                            code VARCHAR(256), 
                            caption VARCHAR(256),
                            user VARCHAR(256), 
                            display_src VARCHAR(256), 
                            is_video VARCHAR(256), 
                            created_at VARCHAR(256))""")
        self.cur.execute("""CREATE TABLE IF NOT EXISTS Image (
                            path VARCHAR(256),
                            url VARCHAR(256),
                            post_id VARCHAR(256) PRIMARY KEY)""")
        self.cur.execute("""CREATE TABLE IF NOT EXISTS SourceImage (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            path VARCHAR(256))""")
        self.cur.execute("""CREATE TABLE IF NOT EXISTS Similarity (
                            value DOUBLE,
                            post_id INTEGER,
                            source_image_id INT,
                            FOREIGN KEY(post_id) REFERENCES Image(post_id),
                            FOREIGN KEY(source_image_id) REFERENCES SourceImage(id))""")
        self.conn.commit()
        self.total_posts = len(self.cur.execute("SELECT * FROM Post").fetchall())

        self.source_image_insert_sql = "INSERT INTO SourceImage(path) VALUES(?)"
        self.post_insert_sql = "INSERT INTO Post(id, code, caption, user, display_src, is_video, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)"
        self.image_insert_sql = "INSERT INTO Image(path, url, post_id) VALUES(?, ?, ?)"
        self.similarity_insert_sql = "INSERT INTO Similarity(value, post_id, source_image_id) VALUES(?, ?, ?)"

    def __del__(self):
        self.cur.close()
        self.conn.close()

    def download_image(self, url, path):
        """
        :param url: image url to download
        :param path: path to save image
        :return: true when download success. if on error, false
        """
        try:
            with open(path, 'wb') as f:
                f.write(self.session.get(url).content)
                return True
        except Exception as e:
            print("download_image Exception: " + e)
            return False

    def compare_image(self, path1, path2, similarity_threshold=0.8):
        try:
            img1 = cv2.imread(path1, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(path2, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None:
                return None

            if img1.shape[1] < img2.shape[1]:
                img2 = img2[:,
                       int((img2.shape[1] - img1.shape[1]) / 2):int(
                           img2.shape[1] + (img2.shape[1] - img1.shape[1]) / 2)]
            elif img2.shape[1] > img1.shape[1]:
                img1 = img1[:,
                       int((img1.shape[1] - img2.shape[1]) / 2):int(
                           img1.shape[1] + (img2.shape[1] - img1.shape[1]) / 2)]

            orb = cv2.ORB_create()

            kp1, des1 = orb.detectAndCompute(img1, None)
            kp2, des2 = orb.detectAndCompute(img2, None)

            # create BFMatcher object
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

            # Match descriptors.
            matches = bf.match(des1, des2)

            similarity = (len(matches) * 2) / (len(kp1) + len(kp2))
            if similarity > similarity_threshold:
                print("Match!")

            """
            # Sort them in the order of their distance.
            matches = sorted(matches, key=lambda x: x.distance)

            # Draw first 10 matches.
            img3 = None
            img3 = cv2.drawMatches(img1, kp1, img2, kp2, matches, flags=2, outImg=img3)

            plt.imshow(img3)
            plt.show()
            """
            return similarity

        except:
            return None

    def save_results(self, instagram_results):
        super().save_results(instagram_results)

        posts = []                                                  #post id 기준으로 db에 없는것만 저장
        self.cur.execute("SELECT id FROM Post")
        id_set = set(map(lambda x: x[0], self.cur.fetchall()))

        for post in instagram_results:
            if post.post_id not in id_set:
                id_set.add(post.post_id)
                posts.append((str(post.post_id),
                              str(post.code),
                              str(post.caption),
                              str(post.user.id),
                              str(post.display_src),
                              str(post.is_video),
                              str(post.created_at)))
        self.cur.executemany(self.post_insert_sql, posts)
        self.conn.commit()
        self.total_posts += len(posts)
        print("[Total Post - %d] %d - Post Inserted" % (self.total_posts, len(posts))) #post id 기준으로 db에 없는것만 저장

        self.cur.execute("SELECT post_id FROM Image")                                  # 각 게시글의 사진을 다운로드 시작
        image_set = set(map(lambda x: x[0], self.cur.fetchall()))
        images = []
        for post in posts:
            if post[0] not in image_set:
                image_set.add(post[0])
                url = post[4]  # display_src
                path = os.path.join(self.storage_path, url.split('/')[-1])
                if self.download_image(url, path):
                    images.append((path, url, post[0]))
        self.cur.executemany(self.image_insert_sql, images)
        self.conn.commit()
        print("%d - Image Downloaded" % (len(images)))                                 # 각 게시글의 사진을 다운로드 끝

        for source_image in self.cur.execute("SELECT id, path FROM SourceImage").fetchall():        #이미지 비교
            source_image_id = source_image[0]
            source_image_path = source_image[1]
            print("Compare with %s" % (source_image_path))

            self.cur.execute(
                "SELECT post_id, path FROM Image WHERE post_id NOT IN (SELECT post_id FROM Similarity WHERE source_image_id=?)",
                (source_image_id,))
            similaritys = []
            for image in self.cur.fetchall():
                image_post_id = image[0]
                image_path = image[1]

                similarity = self.compare_image(source_image_path, image_path)
                if similarity is not None:
                    similaritys.append((similarity, image_post_id, source_image_id))
            self.cur.executemany(self.similarity_insert_sql, similaritys)
            self.conn.commit()
        return self.total_posts
