def count_word_produce_table(myString):
    from collections import Counter
    allWords = myString.lower().split()
    uniqueWords = Counter(allWords)
    uniqueWords = uniqueWords.most_common() #Sort the list by most common words 
    return uniqueWords

def updateHash(myList,uniqueWords):
    for i in uniqueWords:
        if i[0] in myList:
            myList[i[0]]=i[1]+myList.get(i[0])
        else:
            myList[i[0]]=i[1]
    
    return myList
    