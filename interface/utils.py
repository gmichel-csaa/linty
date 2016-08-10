from github import Github
from social.apps.django_app.default.models import UserSocialAuth


def get_github(user):
    if user.is_authenticated():
        try:
            data = UserSocialAuth.objects.filter(user=user).values_list('extra_data')[0][0]
            username = data['login']
            password = data['access_token']

            return Github(username, password)
        except:
            pass

    return Github()


def get_page_number_list(page_num, total_num_pages):
    """
    Returns a list of up to 9 page numbers centered around
    page_num as best it can without going below page 1 or
    above the total number of pages.

    >>> get_page_number_list(3, 4)
    [1, 2, 3, 4]

    >>> get_page_number_list(12, 20)
    [8, 9, 10, 11, 12, 13, 14, 15, 16]

    >>> get_page_number_list(18, 20)
    [12, 13, 14, 15, 16, 17, 18, 19, 20]
    """
    if total_num_pages < 10:
        return range(1, total_num_pages+1)
    elif page_num <= 5:  # Page to center is below 5, print 9 lowest numbers
        return range(1, 10)
    elif total_num_pages - page_num > 4:  # Enough space on both side of number to center
        return range(page_num-4, page_num+5)
    else:  # Page to center around is at or near the end of the range, print last 9 numbers
        return range(total_num_pages-8, total_num_pages+1)
