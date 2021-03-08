import tkinter as tk
import os
import sys
import pandas as pd
import numpy as np
from PIL import Image, ImageTk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
from bs4 import BeautifulSoup
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
from my_functions import img_google


# TODO data browser
class timeline(tk.Tk):
    def __init__(self, filename=os.path.join(os.path.dirname(sys.argv[0]), 'some_dates.csv')):
        tk.Tk.__init__(self)
        self.title("timeline")

        # frame configuration
        self.geometry("%dx%d+0+0" % (self.winfo_screenwidth(), self.winfo_screenheight()))
        tk.Grid.rowconfigure(self, 0, weight=1)
        tk.Grid.rowconfigure(self, 1, weight=2)
        tk.Grid.columnconfigure(self, 0, weight=1)
        tk.Grid.columnconfigure(self, 1, weight=1)
        tk.Grid.columnconfigure(self, 2, weight=1)
        tk.Grid.columnconfigure(self, 3, weight=1)

        self.fr_time = tk.Frame(self)
        self.fr_time.grid(row=0, column=0, sticky="nsew")
        self.fr_cat = tk.Frame(self)
        self.fr_cat.grid(row=0, column=1, sticky="nsew")
        self.fr_scales = tk.Frame(self)
        self.fr_scales.grid(row=0, column=2, sticky="nsew")
        self.fr_img = tk.Frame(self)
        self.fr_img.grid(row=0, column=3, sticky="nsew")
        tk.Grid.rowconfigure(self.fr_img, 0, weight=1)
        tk.Grid.rowconfigure(self.fr_img, 1, weight=4)
        self.colors = pd.Series(['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black'])

        # define scale values
        self.scales_info = pd.DataFrame(columns=['var_name', 'title', 'default_min', 'default_max', 'tot_min', 'tot_max', 'cat_order'])
        self.scales_info.loc[len(self.scales_info)] = ['mya', 'Millions', -4600, 0, -4600, 0, ['supereon', 'eon', 'era', 'period', 'epoch', 'event']]
        self.scales_info.loc[len(self.scales_info)] = ['year', 'years', 1500, 2000, 0, 2019, ["epoch", "person", "art", "event", "invention"]]
        self.scales_info.loc[len(self.scales_info)] = ['ka', 'kilo years', -3000, 0, -1000, 0, ["epoch", "event"]]

        self.scale_type = tk.StringVar()
        self.scale_type.set('year')
        self.myscale = self.scales_info[self.scales_info.var_name == self.scale_type.get()].to_dict('r')[0]

        self.draw_slider()

        # load
        self.filename = filename
        self.df_tot = self.load_data()
        self.df_orig = self.prepare_df(self.df_tot)
        self.c_df = self.draw_cat_toggles()

        # select rows from dataframe
        self.df = self.select_rows_df()

        # self.fr_scales
        for i, scale in self.scales_info.iterrows():
            tk.Radiobutton(self.fr_scales, text=scale.title, variable=self.scale_type, value=scale.var_name, command=self.new_scale).grid(row=i, column=0, sticky='NSEW')

        # self.fr_img: label for item title
        self.label_value = tk.StringVar()
        tk.Label(self.fr_img, textvariable=self.label_value, width=50).pack()
        self.label_value.set('Click on an event!')

        # self.fr_img: label for image
        self.img_label = tk.Label(self.fr_img)
        self.img_label.pack()

        # plotting
        self.draw()

    def draw_slider(self):
        self.yearFrom = tk.IntVar()
        self.yearTo = tk.IntVar()
        self.yearFrom.set(self.myscale['default_min'])
        self.yearTo.set(self.myscale['default_max'])
        scale_length = np.int(self.winfo_screenwidth() / 5)
        slid_min = tk.Scale(self.fr_time, length=scale_length, sliderlength=10, label='Time span:',
                        from_=self.myscale['tot_min'], to=self.myscale['tot_max'], orient=tk.HORIZONTAL, variable=self.yearFrom)
        slid_min.grid(row=0, column=0, sticky='NSEW', padx=4)
        slid_max = tk.Scale(self.fr_time, length=scale_length, sliderlength=10, tickinterval=1000, resolution=1,
                        from_=self.myscale['tot_min'], to=self.myscale['tot_max'], orient=tk.HORIZONTAL, variable=self.yearTo)
        slid_max.grid(row=1, column=0, sticky='NSEW', padx=4)

        # self.fr_time: OK button
        tk.Button(self.fr_time, text="OK", command=self.reset).grid(row=2, column=0, sticky='NSEW')
        self.bind('<Return>', self.reset)

    def draw_cat_toggles(self):
        # create dataframe to store information about categories
        c_df = pd.DataFrame({'category': self.df_orig['category'].unique()})
        c_df['category'] = pd.Categorical(c_df['category'], self.myscale['cat_order'])
        c_df['color'] = self.colors[0:len(c_df)]
        c_df.sort_values('category', inplace=True, ignore_index=True)
        print(c_df)

        # self.fr_cat: toggles for categories displayed
        for i, row in c_df.iterrows():
            # make one toggle field for each category
            c_df.loc[i, 'toggle'] = tk.IntVar()
            tk.Checkbutton(self.fr_cat, fg=c_df.loc[i, 'color'], text=row['category'],
                           variable=c_df.loc[i, 'toggle'], command=self.reset).grid(row=i, column=1, sticky='NSEW')
            c_df.loc[i, 'toggle'].set(1)
        return c_df
    
    def new_scale(self):
        self.myscale = self.scales_info[self.scales_info.var_name == self.scale_type.get()].to_dict('r')[0]
        self.df_orig = self.prepare_df(self.df_tot)
        self.draw_slider()
        self.df = self.select_rows_df()
        self.c_df = self.draw_cat_toggles()
        self.draw()

    def load_data(self):
        df = pd.read_csv(self.filename)
        # replace missing yearOff by yearOn
        df['yearOff'] = np.where(np.isnan(df['yearOff']), df['yearOn'], df['yearOff'])
        df['yearOn'] = df['yearOn'].astype(pd.Int64Dtype())
        df['yearOff'] = df['yearOff'].astype(pd.Int64Dtype())
        return df

    def reset(self, *args):
        self.label_value.set('Click on an event!')
        self.img_label.configure(image=[])
        self.df = self.select_rows_df()
        self.draw()

    def prepare_df(self, df):
        # filter the desired time range
        df = df[df.scale == self.scale_type.get()]
        if self.scale_type.get() == 'mya':
            df.yearOn = -df.yearOn
            df.yearOff = -df.yearOff

        # ignore empty column
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        return df

    def select_rows_df(self, ):
        # pre-process the dataframe to make it suitable for display
        df = self.df_orig.loc[(self.df_orig['yearOn'] >= self.yearFrom.get()) & (self.df_orig['yearOff'] + 1 < self.yearTo.get())]
        # determine minimal length
        min_length = np.int(np.ceil((self.yearTo.get() - self.yearFrom.get()) / self.winfo_screenwidth())) * 2

        # add column for length of event
        df['length'] = df['yearOff'] - df['yearOn']
        df['length'] = np.where(df.length < min_length, min_length, df['length'])

        # show category depending on toggle setting
        for name, row in self.c_df.iterrows():
            state = row['toggle'].get()
            if state == 0:
                # exclude un-toggled categories
                df = df[df['category'] != row['category']]

        # sort and re-index cleaned df
        df['category'] = pd.Categorical(df['category'], self.myscale['cat_order'])
        df = df.sort_values(['category', 'yearOn'])
        df.index = pd.RangeIndex(len(df.index))
        return df

    def draw(self):
        # embed matplotlib figure in widget
        plt.close("all")
        fig = plt.figure()
        ax = plt.subplot(111)
        plt.subplots_adjust(left=0.02, bottom=0.1, right=0.98, top=1, wspace=0, hspace=0)
        plt.xlabel(self.scale_type.get())
        plt.tick_params(axis='y', which='both', left=False, labelleft=False)
        frame_plot = FigureCanvasTkAgg(fig, self)
        frame_plot.get_tk_widget().grid(row=1, column=0, columnspan=4, sticky="nsew")
        linewidth = 1

        # initialize parameters
        my_patches = []
        ypos_group = 0
        ymax = 0

        # loop over categories
        for i, cat_row in self.c_df.iterrows():
            group = self.df[self.df.category == cat_row.category]
            filled = pd.DataFrame(columns=['ypos', 'on', 'off'])
            # draw event as rectangle
            for ind, row in group.iterrows():
                # draw the event in the next free row
                ypos = ypos_group + 1
                # add subsequent pathes directly
                if cat_row.category in ['supereon', 'eon', 'era', 'period', 'epoch']:
                    while any((filled['ypos'] == ypos) & (((filled['on'] < (row['yearOn'])) & ((row['yearOn']) < filled['off'])) | ((filled['on'] < (row['yearOff'])) & ((row['yearOn'] + row['length']) < filled['off'])))):
                        ypos += 1
                    rect = patches.Rectangle((int(row['yearOn']), -(ypos + linewidth)), row['length'], linewidth * 0.9,
                                             facecolor=cat_row.color,
                                             edgecolor='black')
                # start new row for short events
                else:
                    while any((filled['ypos'] == ypos) & (((filled['on'] < (row['yearOn'] - 1)) & ((row['yearOn'] - 1) < filled['off'])) | ((filled['on'] < (row['yearOff'] - 1)) & ((row['yearOn'] + row['length'] + 1) < filled['off'])))):
                        ypos += 1
                    rect = patches.Rectangle((int(row['yearOn']), -(ypos + linewidth)), row['length'], linewidth * 0.9,
                                             facecolor=cat_row.color)
                if ypos > ymax:
                    ymax = ypos
                ax.add_patch(rect)
                my_patches.append(rect)
                filled = filled.append({'ypos': ypos, 'on': row['yearOn'], 'off': row['yearOn'] + row['length']}, ignore_index=True)

            # start a new cateory in a new row
            ypos_group = ymax

        ax.set_xlim(self.yearFrom.get(), self.yearTo.get())
        ax.set_ylim(-(ypos_group + 1), 0)

        # mouse-over function to display event title
        def mouse_over(event):
            for ind, row in self.df.iterrows():
                if my_patches[ind].contains(event)[0]:
                    self.label_value.set(f'{row.title}: {row.yearOn}')

        # mouse-click function for boxes
        def mouse_click(event):
            for ind, row in self.df.iterrows():
                if my_patches[ind].contains(event)[0]:
                    img = img_google.get_tk_img(row['title'])

                    # fix width:
                    #basewidth = 300
                    # wpercent = (basewidth / float(img.size[0]))
                    # hsize = int((float(img.size[1]) * float(wpercent)))
                    # self._im = img.resize((basewidth, hsize), Image.ANTIALIAS)

                    # fix height:
                    hsize = np.int(self.winfo_screenheight() / 5)
                    wpercent = (hsize / float(img.size[1]))
                    basewidth = int((float(img.size[0]) * float(wpercent)))

                    self._im = img.resize((basewidth, hsize), Image.ANTIALIAS)
                    self._image = ImageTk.PhotoImage(self._im)
                    self.img_label.configure(image=self._image)
                    self.label_value.set(row['title'])
                    return

        fig.canvas.mpl_connect('motion_notify_event', mouse_over)
        fig.canvas.mpl_connect('button_press_event', mouse_click)


# mainloop
if __name__ == "__main__":
    root = timeline()
    root.mainloop()
