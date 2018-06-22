import re


class InstagramPost:
    def __init__(self, post_id, code, user=None, caption="", display_src=None, is_video=False, created_at=None):
        """
        A class to represent a post on Instagram
        :param post_id: ID of the post
        :param code: Code of the post
        :param user: A user object representing the owner of the post
        :param caption: The caption/text of the post
        :param display_src: The URL of the image of the post
        :param is_video: A boolean value indicating it's a video
        :param created_at: The time it was created
        """
        self.post_id = post_id
        self.code = code
        self.caption = caption
        self.user = user
        self.display_src = display_src
        self.is_video = is_video
        self.created_at = created_at

    def processed_text(self):
        """
        Processes a caption to remove newlines in it.
        :return:
        """
        if self.caption is None:
            return ""
        else:
            text = re.sub('[\n\r]', ' ', self.caption)
            return text

    def hashtags(self):
        """
        Simple hashtag extractor to return the hastags in the post
        :return:
        """
        hashtags = []
        if self.caption is None:
            return hashtags
        else:
            for tag in re.findall("#[a-zA-Z0-9]+", self.caption):
                hashtags.append(tag)
            return hashtags
