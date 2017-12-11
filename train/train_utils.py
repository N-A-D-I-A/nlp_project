import os, sys, torch, pdb, datetime
from operator import itemgetter
import torch.autograd as autograd
import torch.nn.functional as F
import torch.utils.data as data
import torch.nn as nn
from tqdm import tqdm
import numpy as np
import itertools
import evaluation


def updateScores(args, cs_tensor, similar, i, all_samples):

    scores_list = []

    for j in range(20):

        x = cs_tensor[i, j].data

        if args.cuda:
            x = x.cpu()

        x = x.numpy().item()

        scores_list.append( (x, j) )

    scores_list = sorted(scores_list, reverse = True, key=itemgetter(0))
    binary_scores_list = []

    for j in range(20):
        if scores_list[j][1] in similar:
            binary_scores_list.append(1)
        else:
            binary_scores_list.append(0)

    all_samples.append(binary_scores_list)


def train_model(train_data, dev_data, model, args):
    if args.cuda:
        model = model.cuda()

    parameters = itertools.ifilter(lambda p: p.requires_grad, model.parameters())
    optimizer = torch.optim.Adam(parameters , lr=args.lr, weight_decay=args.weight_decay)

    if args.train:
        model.train()

    for epoch in range(1, args.epochs+1):
        print("-------------\nEpoch {}:\n".format(epoch))

        run_epoch(train_data, True, model, optimizer, args)

        model_path = args.save_path[:args.save_path.rfind(".")] + "_" + str(epoch) + args.save_path[args.save_path.rfind("."):]
        torch.save(model, model_path)

        print "*******dev********"
        run_epoch(dev_data, False, model, optimizer, args)



def test_model(test_data, model, args):
    if args.cuda:
        model = model.cuda()

    print "*******test********"
    run_epoch(test_data, False, model, None, args)


all_samples = []
def run_epoch(data, is_training, model, optimizer, args):
    '''
    Train model for one pass of train data, and return loss, acccuracy
    '''
    data_loader = torch.utils.data.DataLoader(
        data,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        drop_last=True)

    losses = []

    if is_training:
        model.train()
    else:
        model.eval()


    for batch in tqdm(data_loader):

        cosine_similarity = nn.CosineSimilarity(dim=0, eps=1e-6)
        criterion = nn.MultiMarginLoss(margin=0.4)
        #pdb.set_trace()

        if is_training:
            optimizer.zero_grad()

        #out - batch of samples, where every sample is 2d tensor of avg hidden states
        bodies, bodies_masks = autograd.Variable(batch['bodies']), autograd.Variable(batch['bodies_masks'])

        if args.cuda:
            bodies, bodies_masks = bodies.cuda(), bodies_masks.cuda()

        out_bodies = model(bodies, bodies_masks)

        titles, titles_masks = autograd.Variable(batch['titles']), autograd.Variable(batch['titles_masks'])

        if args.cuda:
            titles, titles_masks = titles.cuda(), titles_masks.cuda()

        out_titles = model(titles, titles_masks)

        hidden_rep = (out_bodies + out_titles)/2

        #Calculate cosine similarities here and construct X_scores
        #expected datastructure of hidden_rep = batchsize x number_of_q x hidden_size

        cs_tensor = autograd.Variable(torch.FloatTensor(hidden_rep.size(0), hidden_rep.size(1)-1))

        if args.cuda:
            cs_tensor = cs_tensor.cuda()

        #calculate cosine similarity for every query vs. neg q pair

        for j in range(1, hidden_rep.size(1)):
            for i in range(hidden_rep.size(0)):
                cs_tensor[i, j-1] = cosine_similarity(hidden_rep[i, 0, ], hidden_rep[i, j, ])
                #cs_tensor[i, j-1] = cosine_similarity(hidden_rep[i, 0, ].type(torch.FloatTensor), hidden_rep[i, j, ].type(torch.FloatTensor))

        X_scores = torch.stack(cs_tensor, 0)
        y_targets = autograd.Variable(torch.zeros(hidden_rep.size(0)).type(torch.LongTensor))

        if args.cuda:
                y_targets = y_targets.cuda()

        if is_training:
            loss = criterion(X_scores, y_targets)
            print "Loss in batch", loss.data

            loss.backward()
            optimizer.step()

            losses.append(loss.cpu().data[0])

        else:
            #Average Precision = (sum_{i in j} P@i / j)  where j is the last index

            for i in range(args.batch_size):
                updateScores(args, cs_tensor, batch['similar'][i], i,
                all_samples)

    # Calculate epoch level scores
    if is_training:
        avg_loss = np.mean(losses)
        print('Average Train loss: {:.6f}'.format(avg_loss))
        print()
    else:
        evalobj = evaluation.Evaluation(all_samples)
        print "MAP:", evalobj.MAP()
        print "MRR:", evalobj.MRR()
        print "P@5:", evalobj.Precision(5)
        print "P@1:", evalobj.Precision(1)
