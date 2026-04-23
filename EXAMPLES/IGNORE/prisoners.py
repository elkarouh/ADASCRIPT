import random

boxesnum = list(range(100))      #generate list of 100 boxes
successes=0
failures=0

for i in range(1000):        #iterate process 1000 times
    random1 = list(range(100))
    random.shuffle(random1)       #generate list of numbers from 0 to 99 and shuffle them randomly
    boxes = dict(zip(boxesnum,random1))       #create dictionary mapping each box to a number randomly shuffled
    lastprisoner = 0       #initialize count of prisoners who successfully find their number in the boxes
    for prisoner in boxesnum:
        boxopen = prisoner      #let prisoner start "opening" boxes from the one with his own number (prisoners numbered from 0 to 99)
        boxesopened = 0         #initialize count for number of boxes opened by each prisoner
        while boxesopened < 50:     #let prisoner open up to 50 boxes
            if prisoner == random1[boxopen]:     #if the prisoner opens a box with his own number, skip to next prisoner and add 1 to count of successful prisoners
                lastprisoner += 1
                break
            else:
                boxopen = random1[boxopen]       #next box the prisoner opens is box #(number contained in previous box)
                boxesopened += 1           #update count of boxes opened by the prisoner
        else:
            print("All prisoners are dead!")      #if prisoner has to open more than 50 boxes, stop iteration and all prisoners die
            failures +=1
            break
    if lastprisoner == 100:          
        print("Success!")
        successes+=1
print("success:",successes)
print("failure:",failures)
