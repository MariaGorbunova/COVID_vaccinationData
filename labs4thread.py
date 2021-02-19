# Maria Gorbunova
# Data used: Global survey on coronavirus beliefs, behaviors, and norms: Technical Report
import requests
import json
import tkinter as tk
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Canvas widget
import matplotlib.pyplot as plt  # normal import of pyplot to plot
import tkinter.messagebox as tkmb
matplotlib.use('TkAgg')  # tell matplotlib to work with Tkinter

NUM_WAVES = 15

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
        tk.Button(self, text="OK", command=lambda: self.fetch_data()).grid()

    def on_click_listbox(self, event):
        '''assigns ids for states clicked by user'''
        self.picked_states = [self.listbox.get(idx) for idx in self.listbox.curselection()]

    def fetch_data(self):
        if len(self.picked_states) != 0:
            error_states = []  # for printing it in the error window
            dict_vaccinated = {}  # amount of vaccinated people by state
            dict_waves = {}  # list of acceptance rate through waves for every state
            for state in self.picked_states:
                response = requests.get(
                    f"http://covidsurvey.mit.edu:5000/query?&country=US&us_state={statesDict[state]}&timeseries=true"
                    f"&signal=vaccine_accept").text
                jsonData = json.loads(response)
                print(jsonData)
                
                state_answer_dict = jsonData['all']['vaccine_accept']['weighted']
                dict_vaccinated[state] = state_answer_dict
                if all("error" not in jsonData[item] for item in jsonData.keys()):
                    print("Good state: ", state)
                    waves_list = []
                    # TODO: have to sort it by waves
                    for item in jsonData:
                        print(jsonData[item]['vaccine_accept'])
                        yes = float(jsonData[item]['vaccine_accept']['weighted']['Yes'])
                        vaccinated = 0.0
                        if 'I have already been vaccinated' in jsonData[item]['vaccine_accept']['weighted']:
                            vaccinated = float(
                                jsonData[item]['vaccine_accept']['weighted']['I have already been vaccinated'])
                        waves_list.append(yes + vaccinated)
                    dict_waves[state] = waves_list
                else:
                    error_states.append(state)
                    print("error values in", state)

            if len(error_states) != 0:
                mystr = "No data for " + ', '.join(error_states)
                tkmb.showerror("Error", mystr, parent=self)

            PlotWin(self, dict_waves, 1)
            PlotWin(self, dict_vaccinated, 2)


class PlotWin(tk.Toplevel):
    def __init__(self, master, data, idx):
        super().__init__(master)
        fig = plt.figure(figsize=(6, 6))
        fig.add_subplot(111)

        if idx == 1:
            self.title("Plot vaccine positive trends for states")
            plt.legend(loc="best")
            plt.ylabel("acceptance rate")
            plt.xticks(range(16), rotation=45)
            for state in data:
                print(state)
                print(data[state])
                plt.plot(range(16), data[state], label=state)

        elif idx == 2:
            self.title("Plot the rate of vaccinated people")
            vaccinated = [x['I have already been vaccinated'] for x in data.values()]
            plt.bar(data.keys(), vaccinated, edgecolor='blue')
            plt.ylabel("rate of vaccinated people")
            plt.xlabel("states")
            plt.xticks(rotation=45)

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.get_tk_widget().grid()
        canvas.draw()


MainWin().mainloop()
