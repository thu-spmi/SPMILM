import os
import sys
import numpy as np

sys.path.insert(0, os.getcwd() + '/../../tools/')
import wb
import lstm


def data(tskdir):
    train = tskdir + 'data/train.txt'
    valid = tskdir + 'data/valid.txt'
    test = tskdir + 'data/test.txt'
    return data_verfy([train, valid, test]) + data_wsj92nbest()


def data_verfy(paths):
    for w in paths:
        if not os.path.isfile(w):
            print('[ERROR] no such file: ' + w)
    return paths

def data_wsj92nbest():
    root = './data/WSJ92-test-data/'
    nbest = root + '1000best.sent'
    trans = root + 'transcript.txt'
    ac = root + '1000best.acscore'
    lm = root + '1000best.lmscore'
    return data_verfy([nbest, trans, ac, lm])


if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) == 1:
        print(' \"python run_lstm.py -train\"   train lstm\n '
              ' \"python run_lstm.py -rescore\" rescore nbest\n'
              ' \"python run_lstm.py -wer\"         compute WER'
              )

    fres = wb.FRes('result.txt')
    for tsize in [1, 2, 4]:
        tskdir = '{}/'.format(tsize)
        print(tskdir)
        workdir = tskdir + 'lstmlm/'
        bindir = '../../tools/lstm'
        model = lstm.model(bindir, workdir)

        datas = data(tskdir)
        hidden = 250
        dropout = 0
        epoch = 10
        gpu = 1
        write_model = workdir + 'h{}_dropout{}_epoch{}.lstm'.format(hidden, dropout, epoch)
        write_name = '{}:LSTM:h{}d{}epoch{}'.format(tsize, hidden, dropout, epoch)
        config = '-hidden {} -dropout {} -epoch {}  -gpu {}'.format(hidden, dropout, epoch, gpu)

        if '-train' in sys.argv or '-all' in sys.argv:
            if os.path.exists(write_model):
                print('exist lstm: ' + write_model);
            else:
                model.prepare(datas[0], datas[1], datas[2])
                model.train(write_model, config)

        if '-test' in sys.argv or '-all' in sys.argv:
            PPL = [0]*3
            PPL[0] = model.ppl(write_model, datas[0], config)
            PPL[1] = model.ppl(write_model, datas[1], config)
            PPL[2] = model.ppl(write_model, datas[2], config)
            fres.AddPPL(write_name, PPL, datas[0:3])

        if '-rescore' in sys.argv or '-all' in sys.argv:
            write_lmscore = write_model[0:-5] + '.lmscore'
            model.rescore(write_model, data(tskdir)[3], write_lmscore, config)

        if '-wer' in sys.argv or '-all' in sys.argv:
            [read_nbest, read_templ, read_acscore, read_lmscore] = data(tskdir)[3:7]
            read_lmscore = write_model[0:-5] + '.lmscore'

            [wer, lmscale, acscale] = wb.TuneWER(read_nbest, read_templ,
                                                  read_lmscore, read_acscore, np.linspace(0.1, 0.9, 9))
            print('wer={:.4f} lmscale={:.2f} acscale={:.2f}'.format(wer, lmscale, acscale))
            fres.AddWER(write_name, wer)

            write_templ_txt = workdir + os.path.split(read_templ)[1] + '.w'
            lstm.rmlabel(read_templ, write_templ_txt)
            PPL_templ = model.ppl(write_model, write_templ_txt)
            LL_templ = -wb.PPL2LL(PPL_templ, write_templ_txt)
            fres.Add(write_name, ['LL-wsj', 'PPL-wsj'], [LL_templ, PPL_templ])