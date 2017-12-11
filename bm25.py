import itertools
import train.evaluation as evaluation
from operator import itemgetter

PATH_DEV = "./askubuntu/dev.txt"
PATH_TEST = "./askubuntu/test.txt"

def getSimilarIdx(allq, pos):
    arr = []
    for i, q in enumerate(allq):
        if q in pos:
            arr.append(i)
    return arr

def computeBM25(path):
    all_samples = []
    with open(path) as f:
        for line in f:
            q, pos, allq, bm25 = line.split('\t')
            pos = pos.split()
            allq = allq.split()
            bm25 = bm25.split()
            bm25 = [float(x) for x in bm25]
            similar_idx = getSimilarIdx(allq, pos)

            scores_list = []
            for j in range(len(bm25)):
                scores_list.append( (bm25[j], j) )

            scores_list = sorted(scores_list, reverse = True, key=itemgetter(0))
            binary_scores_list = []

            for j in range(len(bm25)):
                if scores_list[j][1] in similar_idx:
                    binary_scores_list.append(1)
                else:
                    binary_scores_list.append(0)

            all_samples.append(binary_scores_list)

    evalobj = evaluation.Evaluation(all_samples)
    print "MAP:", evalobj.MAP()
    print "MRR:", evalobj.MRR()
    print "P@5:", evalobj.Precision(5)
    print "P@1:", evalobj.Precision(1)

print "****** dev *******"
computeBM25(PATH_DEV)
print "****** test *******"
computeBM25(PATH_TEST)
