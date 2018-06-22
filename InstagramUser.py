class InstagramUser:
    def __init__(self, user_id, username=None, bio=None, followers_count=None, following_count=None, is_private=False):
        """
        A class to represent an Instagram User
        :param user_id: User ID of instagram user
        :param username: Username of Instagram user
        :param bio: Bio text for user
        :param followers_count: Number of followers
        :param following_count: Number of people following
        :param is_private: Boolean to indicate if account is private or not
        """
        self.id = user_id
        self.username = username
        self.bio = bio
        self.followers_count = followers_count
        self.following_count = following_count
        self.is_private = is_private
