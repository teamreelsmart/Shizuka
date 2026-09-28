import math
def page_data(total, page, size=8):
    pages=max(1, math.ceil(total/size)); return max(0,min(page,pages-1)), pages, size
