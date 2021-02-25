# Maria Gorbunova
# LAB 4
# Data used: Global survey on coronavirus beliefs, behaviors, and norms: Technical Report
import os
import re
import time
import json
import requests
import matplotlib
import numpy as np
import tkinter as tk
import tkinter.filedialog
import multiprocessing as mp

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Canvas widget
import matplotlib.pyplot as plt  # normal import of pyplot to plot
import tkinter.messagebox as tkmb

matplotlib.use('TkAgg')  # tell matplotlib to work with Tkinter

NUM_WAVES = 15
DIR_NAME = "lab4dir"
FILE_NAME = "lab4out.txt"
STATESDICT = {
    'Alabama': 'AL',
    'Alaska': 'AK',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Pennsylvania': 'PA',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virginia': 'VA',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY'
}


def set_timer(fct):
    """decorator for response request to print the time """

    def print_stats(*args, **kwargs):
        start = time.time()
        print("Setting the timer on...")
        result = fct(*args, **kwargs)
        print("Requesting response elapsed time: {:.2f}s".format(time.time() - start))
        return result  # returns NoneType if there's no return statement

    return print_stats


def fetch_statedata(state, Q):
    """ gets the response from api, calls other methods to populate dictionaries with prepared data"""
    response = get_response(STATESDICT[state])
    jsonData = json.loads(response)
    error_state = False
    waves_list, vaccinated = for_waves(jsonData)  # getting the list of waves and num of vaccinated ppl
    if waves_list.count(0.0) >= NUM_WAVES // 2:
        error_state = True  # getting the list of states with no data to print error message
    else:
        cleanup_data(waves_list)  # find average of the neighbors
    Q.put((state, error_state, vaccinated, waves_list))


@set_timer
def get_response(val):
    """calling the api and getting the response"""
    return requests.get(
        f"http://covidsurvey.mit.edu:5000/query?&country=US&us_state={val}&timeseries=true"
        f"&signal=vaccine_accept").text


def for_waves(jsonData):
    """Accepts jsonData - a dictionary of data for state, collects the data
    for each wave for a certain state and returns sorted list of waves """
    waves_list, waves_sort = [], []
    vaccinated = 0
    # result of this for loop is unsorted waves_list for one state
    for wave in jsonData:
        if 'all' not in wave:  # collect data through all waves
            waves_sort.append(int(re.findall(r'\d+', wave)[0]))
            try:
                yes = float(jsonData[wave]['vaccine_accept']['weighted']['Yes'])
                if 'I have already been vaccinated' in jsonData[wave]['vaccine_accept']['weighted']:
                    vaccinated = float(
                        jsonData[wave]['vaccine_accept']['weighted']['I have already been vaccinated'])
                    yes += vaccinated
            except KeyError:
                yes = 0.0
            waves_list.append(yes)
    permutation = np.argsort(waves_sort)  # sort the waves (not in order:  1 10 11 12... 2 3 4 ...)
    return [waves_list[i] for i in permutation], vaccinated


def cleanup_data(waves_list):
    """check the neighbors and find avg"""
    # TODO: not happy with this
    for i, item in enumerate(waves_list):
        if item == 0.0:
            if i == 0 or waves_list[i - 1] == 0.0:
                try:
                    item = waves_list[i + 1]
                except IndexError:
                    print(item, i, len(waves_list))
            elif i == len(waves_list) - 1 or waves_list[i + 1] == 0.0:
                item = waves_list[i - 1]
            # else waves_list[i + 1] == 0.0 and waves_list[i - 1] == 0.0:
            # item = sum(waves_list) / len(waves_list)
            else:
                item = (waves_list[i - 1] + waves_list[i + 1]) / 2
            waves_list[i] = item


class MainWin(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vaccine Survey")
        self.label = tk.Label(self, text="Click on state names to choose states").grid()
        self.content_frame = tk.Frame(self)
        self.scrollbar = tk.Scrollbar(self.content_frame)
        self.scrollbar.pack(side='right', fill='y')
        self.listbox = tk.Listbox(self.content_frame, height=10, width=30, selectmode="multiple")
        self.listbox.insert(tk.END, *STATESDICT.keys())
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.pack()
        self.content_frame.grid()
        tk.Button(self, text="OK", command=lambda: self.do_work()).grid()
        self.protocol("WM_DELETE_WINDOW", self.exit_fct)

    def do_work(self):
        """ in case user picked some states from the list then will call other
        methods to do the work using threads and will create 2 instances of the PlotWin class """
        picked_states = [self.listbox.get(idx) for idx in self.listbox.curselection()]
        if picked_states:
            error_states = []  # for printing it in the error window
            dict_vaccinated = {}  # amount of vaccinated people by state
            dict_waves = {}  # list of acceptance rate through waves for every state
            start = time.time()
            """for state in self.picked_states:
                self.fetch_statedata(state, error_states, dict_vaccinated, dict_waves)
            # 1.94s for the simple loop"""

            Q = mp.Queue()
            procs = []  # create a list of processes, each will run function fetch_statedata
            for state in picked_states:
                p = mp.Process(target=fetch_statedata,
                               args=(state, Q))
                procs.append(p)
                p.start()
            while any(p.is_alive() for p in procs):
                if not Q.empty():
                    mytuple = Q.get()
                    if mytuple[1]:  # in case its an error state
                        error_states.append(mytuple[0])
                    else:
                        dict_vaccinated[mytuple[0]] = mytuple[2]
                        dict_waves[mytuple[0]] = mytuple[3]
            for p in procs:
                p.join()
            print("~*~*~*~*~*~*~*~ Total elapsed time: {:.2f}s ~*~*~*~*~*~*~*~".format(time.time() - start))
            # Total elapsed time: 0.60s for threads
            # Total elapsed time: 2.45ss for procs

            if error_states:
                mystr = "No data for " + ', '.join(error_states)
                tkmb.showerror("Error", mystr, parent=self)

            # wait for the second window to be closed
            PlotWin(self, dict_waves, 'trend')
            self.wait_window(PlotWin(self, dict_vaccinated, 'vaccinated'))

            self.save_file(dict_waves, dict_vaccinated)
            self.listbox.selection_clear(0, tk.END)

    def exit_fct(self):
        """ closes the window, exits the program"""
        self.destroy()
        self.quit()

    def save_file(self, dict_waves, dict_vaccinated):
        """saves data on chosen states to a file in a certain directory"""
        if tkmb.askokcancel("Save", "Save result to file?", parent=self):
            directory = tk.filedialog.askdirectory(initialdir=os.getcwd())
            path = os.path.join(directory, DIR_NAME)
            if DIR_NAME not in os.listdir():
                os.mkdir(path)
            # os.chdir(path)  # either change dir, or append the path to the filename
            filename_address = os.path.join(path, FILE_NAME)
            with open(filename_address, "w") as file:
                for state in dict_waves:
                    file.write(state + '\n')
                    liststr = ', '.join(map(str, dict_waves[state]))
                    file.write("approve: " + liststr + '\n')
                    file.write("vaccinated: " + str(dict_vaccinated[state]) + '\n')


class PlotWin(tk.Toplevel):
    def __init__(self, master, data, option):
        super().__init__(master)
        fig = plt.figure(figsize=(5, 5))
        fig.add_subplot(111)
        if option == 'trend':
            self.title("Vaccine positive trends for states")
            plt.ylabel("acceptance rate")
            plt.xlabel("waves")
            plt.xticks(range(1, NUM_WAVES + 1), rotation=45)
            for state in data:
                plt.plot(range(1, NUM_WAVES + 1), data[state], label=state)
                plt.legend(loc="best")
        elif option == 'vaccinated':
            self.title("Rate of vaccinated people")
            vaccinated = [x for x in data.values()]
            plt.bar(data.keys(), vaccinated, edgecolor='black')
            plt.ylabel("rate of vaccinated people")
            plt.xlabel("states")
            plt.xticks(rotation=45)
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.get_tk_widget().grid()
        canvas.draw()


if __name__ == '__main__':
    MainWin().mainloop()


'''
ANALYSIS
For the experience I picked first 10 states for all of the tests.

This is the time results that ive got:

for loop
~*~*~*~*~*~*~*~ Total elapsed time: 6.50s ~*~*~*~*~*~*~*~
Explanation: 
this way is the sowest because it calls the api one time at a time,
so it is a sum of time of every request.

threads:
~*~*~*~*~*~*~*~ Total elapsed time: 0.67s ~*~*~*~*~*~*~*~
Explanation: 
this way is the fastest because it starts threads and they all request for info.
The memory is shared and they populate what i need 'simultaneously'

processes:
~*~*~*~*~*~*~*~ Total elapsed time: 2.21s ~*~*~*~*~*~*~*~
Explanation: 
this way is slightly slower than the threads and fatser than loop.
each process requests the data from the api,the memory is not shared for them.
In order to keep all retireved data for each state I had to use queue.
The need to exchange data through different processes slows down the elapsed time 

'''


