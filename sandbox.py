try:
    import cPickle as pickle
except:
    import pickle

test = True

a = pickle.dumps(test)

b = pickle.loads(a)

print(b)