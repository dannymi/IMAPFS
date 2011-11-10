#!/usr/bin/env python

# wrong

import time

def mkgmtime(human_time):
    utc = time.mktime(human_time[:9])

    try:
        zone = human_time[9]
    except:
        zone = 0 # oob

    # Following is necessary because the time module has no 'mkgmtime'.
    # 'mktime' assumes arg in local timezone, so adds timezone/altzone.

    lt = time.localtime(utc)
    if time.daylight and lt[-1]:
        zone = zone + time.altzone
    else:
        zone = zone + time.timezone

    return time.mktime(time.localtime(utc - zone))

if __name__ == "__main__":
	print mkgmtime(time.localtime())

	print mkgmtime((2007, 4, 30, 16, 57, 50, 0, 1, 0, 7200))
	print mkgmtime((2007, 3, 8, 21, 5, 36, 0, 1, 0, 7200))


