import sys
import os
import subprocess
import csv
import time
import atexit

PORT = '21452'
TARGET = 'http://127.0.0.1:{}/'.format(PORT)
CSV_BASE = os.path.join(os.path.dirname(__file__), 'perf_')
CSV_BASELINE = CSV_BASE + 'baseline.csv'
CSV_CURRENT = CSV_BASE + 'current.csv'


def ab(fname_csv):
    cmd = ['ab', '-n', '4000', '-c', '50', '-e', fname_csv, TARGET]
    subprocess.check_call(cmd)


def read(fname):
    data = {}
    with open(fname) as f:
        reader = csv.reader(f)
        reader.next()
        for line in reader:
            data[int(line[0])] = float(line[1])
    return data


def compare_perc(baseline, current):
    p = (current-baseline) / baseline * 100
    # TODO color
    return '{:10}\t{:10}\t{:10.2f} %'.format(baseline, current, p)

def compare():
    baseline = read(CSV_BASELINE)
    current = read(CSV_CURRENT)

    for perc in [0, 95, 100]:
        print '{:3}'.format(perc), compare_perc(baseline[perc], current[perc])


def main():
    proc = subprocess.Popen(['rw', 'serv', '-p', PORT, 'test.example'])
    atexit.register(proc.terminate)

    if 'baseline' in sys.argv:
        print 'testing baseline'
        fname = CSV_BASELINE

        if os.path.exists(CSV_CURRENT):
            os.unlink(CSV_CURRENT)
    else:
        fname = CSV_CURRENT

    # wait to be sure rw process is done starting
    # TODO maybe check if actually running?
    time.sleep(0.5)
    ab(fname)

    if os.path.exists(CSV_CURRENT) and os.path.exists(CSV_BASELINE):
        compare()



if __name__ == '__main__':
    main()
