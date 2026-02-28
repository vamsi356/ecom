import random
ucase_letter=[chr(i) for i in range(ord('A'),ord('Z')+1)]
lcase_letter=[chr(i) for i in range(ord('a'),ord('z')+1)]
def genotp():
    otp=''
    for i in range(2):
        otp=otp+random.choice(ucase_letter)
        otp=otp+random.choice(lcase_letter)
        otp=otp+str(random.randint(0,9))
    return otp
