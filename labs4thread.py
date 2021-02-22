# Maria Gorbunova
# LAB 4
# Data used: Global survey on coronavirus beliefs, behaviors, and norms: Technical Report
import re
import time
import json
import requests
import threading
import matplotlib
import numpy as np
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Canvas widget
import matplotlib.pyplot as plt  # normal import of pyplot to plot
import tkinter.messagebox as tkmb

matplotlib.use('TkAgg')  # tell matplotlib to work with Tkinter

NUM_WAVES = 15

DEBUG = False

statesDict = {
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
    def print_stats(*args, **kwargs):
        start = time.time()
        print("Setting the timer on...")
        result = fct(*args, **kwargs)
        print("Requesting response elapsed time: {:.2f}s".format(time.time()-start))
        return result  # returns NoneType if theres no return sttmnt

    return print_stats


class MainWin(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vaccine Survey")
        self.picked_states = []
        self.label = tk.Label(self, text="Click on state names to choose states").grid()
        self.content_frame = tk.Frame(self)
        self.scrollbar = tk.Scrollbar(self.content_frame)
        self.scrollbar.pack(side='right', fill='y')
        self.listbox = tk.Listbox(self.content_frame, height=10, width=30, selectmode="multiple")
        self.listbox.insert(tk.END, *statesDict.keys())
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.pack()
        self.content_frame.grid()
        self.listbox.bind('<ButtonRelease-1>', self.on_click_listbox)
        self.tk.Button(self, text="OK", command=lambda: self.do_work()).grid()

    def on_click_listbox(self, event):
        """ assigns ids for states clicked by user to picked_states """
        self.picked_states = [self.listbox.get(idx) for idx in self.listbox.curselection()]

    def do_work(self):
        """ in case user picked some states from the list
         this method will request data from the covidsurvey.mit in json format
         then will populate the data needed for plotting
         and will create instances of the PlotWin class """
        if len(self.picked_states) != 0:
            error_states = []  # for printing it in the error window
            dict_vaccinated = {}  # amount of vaccinated people by state
            dict_waves = {}  # list of acceptance rate through waves for every state

            start = time.time()

            """for state in self.picked_states:
                self.fetch_statedata(state, error_states, dict_vaccinated, dict_waves)
            # 1.94s for the simple loop
            print("~*~*~*~*~*~*~*~ Total elapsed time: {:.2f}s ~*~*~*~*~*~*~*~".format(time.time() - start))"""

            threads = []  # create a list of threads, each thread will run function fetch_statedata
            for state in self.picked_states:
                t = threading.Thread(target=self.fetch_statedata,
                                     args=(state, error_states, dict_vaccinated, dict_waves))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()
            print("~*~*~*~*~*~*~*~ Total elapsed time: {:.2f}s ~*~*~*~*~*~*~*~".format(time.time() - start))

            if len(error_states) != 0:
                mystr = "No data for " + ', '.join(error_states)
                tkmb.showerror("Error", mystr, parent=self)

            PlotWin(self, dict_waves, 'trend')
            PlotWin(self, dict_vaccinated, 'vaccinated')

    def fetch_statedata(self, state, error_states, dict_vaccinated, dict_waves):
        response = self.get_response(statesDict[state])

        jsonData = json.loads(response)
        if DEBUG:
            print(jsonData)

        # this data is for plotting the vaccinated for states
        # Comment: could move it to the else so it is populated only by not faulty states.
        dict_vaccinated[state] = float(
            jsonData['all']['vaccine_accept']['weighted']["I have already been vaccinated"])

        # getting the list of waves and the list for sorting in the next step
        # Comment: I could either sort it in for_waves or do it like i did here
        # I did it this way because I don't want to sort waves that have a lot of error values
        waves_list, waves_sort = self.for_waves(jsonData)

        if waves_list.count(-0.1) > 2:
            # getting the list of states with no/little data to print error message
            error_states.append(state)
        else:
            # TODO: clean up data (add average value)
            # assigning sorted waves to states in dictionary
            dict_waves[state] = self.sorted_waves(waves_list, waves_sort)

    @set_timer
    def get_response(self, val):
        """calling the api and getting the responce"""
        return requests.get(
            f"http://covidsurvey.mit.edu:5000/query?&country=US&us_state={val}&timeseries=true"
            f"&signal=vaccine_accept").text

    def for_waves(self, jsonData):
        """Accepts jsonData - a dictionary of data for state,
        collects the data for each wave for a certain state
        returns sorted list of waves
        * we will need to sort the order of waves later
        """
        waves_list, waves_sort = [], []
        # result of this for loop is unsorted waves_list for one state
        for wave in jsonData:
            if 'all' not in wave:  # collect data through all waves
                waves_sort.append(int(re.findall(r'\d+', wave)[0]))  # need to figure out the order of waves
                try:
                    if DEBUG:
                        print('jsonData[wave]', jsonData[wave])
                        print("jsonData[wave]['vaccine_accept']", jsonData[wave]['vaccine_accept'])
                    yes = float(jsonData[wave]['vaccine_accept']['weighted']['Yes'])
                    if 'I have already been vaccinated' in jsonData[wave]['vaccine_accept']['weighted']:
                        yes += float(
                            jsonData[wave]['vaccine_accept']['weighted']['I have already been vaccinated'])
                    waves_list.append(yes)
                except KeyError:
                    if DEBUG:
                        print("Error! Replacing values to (-0.1) for : ", jsonData[wave])
                    waves_list.append(-0.1)
        return waves_list, waves_sort

    def sorted_waves(self, unsorted_waves, idx_sortby):
        # a = np.array(idx_sortby) # Question: can argsort python list? - seems to work
        permutation = np.argsort(idx_sortby)
        if DEBUG:
            print('*' * 20, 'SORTING WAVES', '*' * 20)
            print("Index to sort by: ", idx_sortby)
            print("Permutation: ", permutation)
            print("Unsorted waves: ", unsorted_waves)
            print("Sorted waves:   ", [unsorted_waves[i] for i in permutation])
            print('*' * 55)
        return [unsorted_waves[i] for i in permutation]


class PlotWin(tk.Toplevel):
    def __init__(self, master, data, option):
        super().__init__(master)
        fig = plt.figure(figsize=(5, 5))
        fig.add_subplot(111)

        if option == 'trend':
            self.title("Plot vaccine positive trends for states")
            plt.ylabel("acceptance rate")
            plt.xticks(range(NUM_WAVES), rotation=45)
            # TODO: print waves pretty
            for state in data:
                plt.plot(range(NUM_WAVES), data[state], label=state)
                plt.legend(loc="best")

        elif option == 'vaccinated':
            self.title("Plot the rate of vaccinated people")
            vaccinated = [x for x in data.values()]
            plt.bar(data.keys(), vaccinated, edgecolor='black')
            plt.ylabel("rate of vaccinated people")
            plt.xlabel("states")
            plt.xticks(rotation=45)

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.get_tk_widget().grid()
        canvas.draw()


MainWin().mainloop()
