# Maria Gorbunova
# LAB 4
# Data used: Global survey on coronavirus beliefs, behaviors, and norms: Technical Report
""" The program calls API using threads and fetches the data on COVID"""
# Revised my code with Ben Lublin: our code is not identical!

import os
import re
import time
import json
import requests
import threading
import matplotlib
import numpy as np
import tkinter as tk
import tkinter.filedialog

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
        tk.Button(self, text="OK", command=self.do_work).grid()
        self.protocol("WM_DELETE_WINDOW", self.quit)

    def do_work(self):
        """ in case user picked some states from the list then will call other
        methods to do the work using threads and will create 2 instances of the PlotWin class """
        picked_states = [self.listbox.get(idx) for idx in self.listbox.curselection()]
        if picked_states:
            error_states = []  # for printing it in the error window
            dict_vaccinated = {}  # amount of vaccinated people by state
            dict_waves = {}  # list of acceptance rate through waves for every state
            start = time.time()
            """for state in picked_states:
                self.fetch_statedata(state, error_states, dict_vaccinated, dict_waves)
            print("~*~*~*~*~*~*~*~ Total elapsed time: {:.2f}s ~*~*~*~*~*~*~*~".format(time.time() - start))
            #~*~*~*~*~*~*~*~ Total elapsed time: 6.50s ~*~*~*~*~*~*~*~"""
            # Did not use queue because there is no race condition.
            # I use list and dictionaries, and they are thread safe containers
            # I only do one time operation on them
            # and I don't really care about the order the containers get populated
            threads = []  # create a list of threads, each thread will run function fetch_statedata
            for state in picked_states:
                t = threading.Thread(target=self.fetch_statedata,
                                     args=(state, error_states, dict_vaccinated, dict_waves))
                threads.append(t)
                t.start()
            for t in threads:  # does it stop the loop to wait for a slow thread to join?
                t.join()
            print("~*~*~*~*~*~*~*~ Total elapsed time: {:.2f}s ~*~*~*~*~*~*~*~".format(time.time() - start))
            # Total elapsed time: 0.60s for threads
            if error_states:
                tkmb.showerror("Error", f"No data for:\n{', '.join(error_states)}", parent=self)

            # wait for the second window to be closed
            PlotWin(self, dict_waves, 'trend')
            self.wait_window(PlotWin(self, dict_vaccinated, 'vaccinated'))

            self.save_file(dict_waves, dict_vaccinated)
            self.listbox.selection_clear(0, tk.END)

    def save_file(self, dict_waves, dict_vaccinated):
        if tkmb.askokcancel("Save", "Save result to file?", parent=self):
            directory = tk.filedialog.askdirectory(initialdir='.')
            os.chdir(directory)
            # path = os.path.join(directory, DIR_NAME)
            if DIR_NAME not in os.listdir(directory):
                os.mkdir(DIR_NAME)
            # os.chdir(path)  # either change dir, or append the path to the filename
            # filename_address = os.path.join(path, FILE_NAME)
            os.chdir(DIR_NAME)
            with open(FILE_NAME, "w") as file:
                for state in dict_waves:
                    file.write(state + '\n')
                    liststr = ', '.join(map(str, dict_waves[state]))
                    file.write("approve: " + liststr + '\n')
                    file.write("vaccinated: " + str(dict_vaccinated[state]) + '\n')

    def fetch_statedata(self, state, error_states, dict_vaccinated, dict_waves):
        """ gets the response from api, calls other methods to populate dictionaries with prepared data"""
        response = self.get_response(STATESDICT[state])
        jsonData = json.loads(response)
        waves_list, vaccinated = self.for_waves(jsonData)  # getting the list of waves and num of vaccinated ppl
        if waves_list.count(0.0) >= NUM_WAVES // 2:  # if more than a half data missing - bad data
            error_states.append(state)  # getting the list of states with no data to print error message
        else:
            self.cleanup_data(waves_list)  # find average of the neighbors
            # data are stored into or removed from the container in a single operation.
            dict_waves[state] = waves_list
            dict_vaccinated[state] = vaccinated  # for plotting the vaccinated for states

    @set_timer
    def get_response(self, val):
        """calling the api and getting the response"""
        return requests.get(f"http://covidsurvey.mit.edu:5000/query?country=US&us_state={val}&signal=vaccine_accept&timeseries=true").text
            #f"http://covidsurvey.mit.edu:5000/query?&country=US&us_state={val}&timeseries=true&signal=vaccine_accept").text

    def for_waves(self, jsonData):
        """Accepts jsonData - a dictionary of data for state, collects the data
        for each wave for a certain state and returns sorted list of waves """
        waves_list, waves_sort = [], []
        vaccinated = 0
        # result of this for loop is unsorted waves_list for one state
        for wave in jsonData:
            if 'all' not in wave:  # collect data through all waves
                waves_sort.append(int(re.findall(r'\d+', wave)[0]))
                try:
                    yes = jsonData[wave]['vaccine_accept']['weighted']['Yes']
                    if 'I have already been vaccinated' in jsonData[wave]['vaccine_accept']['weighted']:
                        vaccinated = jsonData[wave]['vaccine_accept']['weighted']['I have already been vaccinated']
                        yes += vaccinated
                except KeyError:
                    yes = 0.0
                waves_list.append(yes)
        permutation = np.argsort(waves_sort)  # sort the waves (not in order:  1 10 11 12... 2 3 4 ...)
        return [waves_list[i] for i in permutation], vaccinated

    def cleanup_data(self, waves_list):
        """check the neighbors and find avg"""
        for i, item in enumerate(waves_list):
            if item == 0.0:
                if i == 0 and waves_list[i + 1] != 0.0:  # if first and no next
                    item = waves_list[i + 1]
                elif i == len(waves_list) - 1 or (waves_list[i + 1] == 0.0 and i != 0):  # if last or no next
                    item = waves_list[i - 1]
                elif waves_list[i + 1] != 0.0 and waves_list[i - 1] != 0.0:  # if there's prev and next val
                    item = (waves_list[i - 1] + waves_list[i + 1]) / 2
                else:  # find average for non zero vals
                    item = sum(waves_list) / (len(waves_list) - waves_list.count(0.0))
                waves_list[i] = item


class PlotWin(tk.Toplevel):
    def __init__(self, master, data, option):
        super().__init__(master)
        fig = plt.figure(figsize=(5, 5))
        if option == 'trend':
            self.title("Vaccine positive trends for states")
            plt.ylabel("acceptance rate(%)")
            plt.xlabel("waves")
            plt.xticks(range(1, NUM_WAVES + 1))
            for state in data:
                plt.plot(range(1, NUM_WAVES + 1), [x * 100 for x in data[state]], label=state)
                plt.legend(loc='best', fontsize='small')
        elif option == 'vaccinated':
            self.title("Rate of vaccinated people")
            plt.bar(data.keys(), [x * 100 for x in data.values()], edgecolor='black')
            plt.ylabel("rate of vaccinated people(%)")
            plt.xlabel("states")
            plt.xticks(rotation=45)
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.get_tk_widget().grid()
        canvas.draw()


if __name__ == '__main__':
    MainWin().mainloop()
