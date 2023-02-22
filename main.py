
"""
BRUK:
----------------------
Gitt en mappe med bilder (src) flytt disse bildene sortert etter år og måned
til en annen mappe (dst).

Bilder med "Screenshot" i navnet legges i separat hierarki i (dst) men med struktur.

Bilder uten exif-date kan forsøke å sorteres ved å se på os-date.
For egne filer ser da "modified" ut til å stemme godt.

en annen løsning er å se på navnet. Ofte har bildene dato som del av navnet.

modified ser også ut til å stemme for bilder mottatt. Ofte kan man ønske å sortere de
på år/mnd da bildet ble mottatt (var relevant) og ikke når bildet en eller annen gang ble tatt/laget

-  -  -  -  -  -  -  -

(eget bruk)
Husk å se over options av globale variable. Flags/switches
Husk å se over lista med aksepterte filformater.



UTBEDRING:
-----------------------

* Undersøk konstanter som kan breake programmet

* Sjekk hva som skjer om antall filer i source er få:
     Hva skjer med 'pb_max - 1'
     Virker som dette faktisk går bra fordi prosessen kjøres ferdig lenge før de 200 ms update er satt til.
        så den hopper direkte til 100% og avbryter kall til update så koden kjøres aldri..?

* Filer uten exif-date ser ut til å ha riktig date gitt som 'file modified date'

* Undersøk hvordan programmet kunne vært mer modulisert/clanere/oversiktlig/håndterlig


LEGG TIL:
------------------------

* Tester

* stop processing- knapp?

* filcount ved siden av %?

* live view av folders/filer som behandles?

* sjekk om jps/tiff, om ikke bruk os/navn til å finne date.



OBSERVASJONER:
----------------------

Ser ut til at den senere tiden har snap begynt å bruke dato i navnet.
snapfilene har ofte ikke exif, men modified ser riktig ut.
Om nylig, kan man også sjekke navnet på dem for dato.

Bli bedre på språk og navngivning


"""





# ~~~~~~~~~~~~~~~~~~~~~~~~
#        IMPORTS
# ~~~~~~~~~~~~~~~~~~~~~~~~


import tkinter as tk
from tkinter import filedialog, ttk, VERTICAL
import os
from os import path, makedirs, walk
import shutil
from datetime import datetime
import calendar
import exifread
import time

# ~~~~~~~~~~~~~~~~~~~~~~~~
#        GLOBALS
# ~~~~~~~~~~~~~~~~~~~~~~~~

root_src_dir = ""        # source directory
root_dst_dir = ""        # destination directory
pb_max = 0               # progressbar max value (settes etter src folder)
DISP_PATH_LEN = 55       # displayed path length (min 20)
SCHD_TIME = 200          # progressbar update frequency ms
files_in_src_before = 0
accumulated_progress = 0

EXT_IMAGE = ["jpg", "jpeg", "tif", "JPG"]  # accepted file types

FORMATCODE_EXIF = "%Y:%m:%d %H:%M:%S"
FORMATCODE_OS = "%a %b %d %H:%M:%S %Y"

TAG_ORGINAL = "DateTimeOrginal"
TAG_DIGITIZED = "DateTimeDigitized"
TAG_DATETIME = "DateTime"

counter_files_moved = 0         # files moved
counter_files_counted = 0       # files counted between progressbar updates
counter_files_counted_accum = 0 # samlet antall filer telt i curr telling

current_scheduled_update = ""   # For hver 'after'-call oppdateres denne med schedule-ID for å kunne håndtere/avbryte
coherent_icon = "C:\\Users\\47991\\PycharmProjects\\basicgui\\images\\coherent logo.ico" # Window icon

# flags
move_processed_files = True  # if True, files can be moved
live_info_print = True       # debug print
close_requested_flag = False # user tried to close application
running_flag = False         # processing
failed_source = False
failed_destination = False

include_os_dates = False     # inkluderer os dates
include_exif_dates = True    # inkluderer exifdata

# ~~~~~~~~~~~~~~~~~~~~~~~~
#       FUNCTIONS
# ~~~~~~~~~~~~~~~~~~~~~~~~

def get_cropped_path(path):
    global DISP_PATH_LEN
    """cropping the filepath string to length DISP_PATH_LEN"""
    start = path[:10]
    mid = "....."
    l = DISP_PATH_LEN - len(start) - len(mid)
    diff = len(path) - l
    cropped_path = start + mid + path[diff:]
    return cropped_path
def print2(string):
    """Print wrapper to controll prints with a switch"""
    global live_info_print
    if live_info_print:
        print(string)
def get_date_taken(file):
    # not reviewd
    global FORMATCODE_EXIF
    """
    Henter ut opp til 5 date-stamps tilknyttet file
    og returnerer laveste eller ''
    input:  path to image
    output: datetime object (oldest of the 5 dates)
            ""              (no dats found)
    """
    dates = []

    if include_exif_dates:
        try:
            with open(file, 'rb') as f:
                tags = exifread.process_file(f)
                for tag in tags.keys():
                    if tag == "EXIF DateTimeOriginal":
                        date = str(tags[tag])
                        if date:
                            dates.append(datetime.strptime(date, FORMATCODE_EXIF))

                    elif tag == "Image DateTime":
                        date = str(tags[tag])
                        if date:
                            dates.append(datetime.strptime(date, FORMATCODE_EXIF))

                    elif tag == "EXIF DateTimeDigitized":
                        date = str(tags[tag])
                        if date:
                            dates.append(datetime.strptime(date, FORMATCODE_EXIF))
        except ValueError as v:
            valid_date = process_invalid_date_format(date, file)
            print2(f"{file} :: {v}")
            if valid_date:
                dates.append(datetime.strptime(valid_date, FORMATCODE_EXIF))
        except Warning as w:
            print2(f"{file} :: {w}")


    if include_os_dates:
        try:
            modified = path.getmtime(file)
            date = time.ctime(modified)
            if date:
                dates.append(datetime.strptime(date, FORMATCODE_OS))

            created = path.getctime(file)
            date = time.ctime(created)
            if date:
                dates.append(datetime.strptime(date, FORMATCODE_OS))

        except OSError as o:
            print2(f"File does'nt exist or inaccessible\n{file}\n{o}\n")


    if dates:
        oldest = min(dates)
        return oldest
    else:
        print(f"Found no dates\n{file}\n")
        return ""
def process_invalid_date_format(date, file):
    """
    date has the form YYYY:MM:DD HH:MM:SS
    for when the HH is set wrong at midnight.
    For file with date format 2017:08:10 24:30:39
    :return: returns correct format (would be 00:30:39 for the example)
    """
    #check format

    try:
        splittet = date.split()
        year, month, day = splittet[0].split(":")
        hour, minute, second = splittet[1].split(":")

        # unknown date
        if year == "0000":
            print2(f"{date} Cant formate date in file: {file}\n")
            return

        # wrong formating. Assume rest is correct
        if hour == "24":
            #print2(f"{year}:{month}:{day} 00:{minute}:{second}")
            return f"{year}:{month}:{day} 00:{minute}:{second}"

    except IndexError as i:
        print2(f"{date} ::: {i} in file: {file}\n")
        return

    except SyntaxError as s:
        print2(f"{date} ::: {s} in file {file}\n")
        return

    except ValueError as v:
        print2(f"{date} ::: {v} in file: {file}\n")
        return
def accepted_file(filename):
    split = filename.split(".")
    ext = split[-1]
    if len(split) >= 2 and ext in EXT_IMAGE:
        return True
    else:
        return False
def help_window():
    help_window = tk.Toplevel(root)
    help_window.title("Coherent"+" "*24 + "Brukerveiledning")
    help_window.minsize(400, 150)
    help_window.resizable(False, False)
    help_window.iconbitmap(coherent_icon)

    veiledning = tk.Label(
        help_window,
        text="Sorterer alle bilder med jpeg- og tiff-format med gyldig dato satt av device\n"
             "Andre filtyper ignoreres\n"
             "om bilder av gitt format ikke sorters var det ikke mulig å hente ut dato informasjon.\n\n"
             "1) 'Source folder'\nVelg mappen med bilder du ønsker å sortere\n\n"
             "2) 'Destination folder'\nVelg mappen der du ønsker at bildene skal flyttes\n\n"
             "3) 'run'\nSjekk at de valgte mappene stemmer, trykk så 'run' for å"
             " starte sorteringen"
    )
    veiledning.pack()
def count_folder(folder):
    """ given folder, returns total number of files and accepted files defined in accepted_files() """
    file_count = 0
    accepted = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in filenames:
            file_count += 1
            if accepted_file(filename):
                accepted += 1
    return file_count, accepted
def close_requested():
    """  Defining whats going to happen if user tries to close the main window """
    global close_requested_flag

    if not running_flag:
        #print(f"<{root.tk.call('after', 'info')}>") current scheduled call
        #print(f"close requested, running_flag is {running_flag}, closing executed directly")
        exit(0)
    else:
        #print(f"running_flag is {running_flag}, trying to close asap, setting close requested_flag")
        close_requested_flag = True
        #print(f"close requested flag set to {close_requested_flag}")
def set_src_folder():
    """ Lets the user set the source folder using a file chooser """
    global root_src_dir, pb_max, files_in_src_before, run_label, failed_source, root

    if failed_source:
        run_label['text'] = ""

    folderpath = filedialog.askdirectory()

    #root.update() lag?

    if folderpath:
        root_src_dir = folderpath   # global holding the actual src dir path
        displayed_path = folderpath # path to be displayed in label

        # crop string if path too long for label
        if len(displayed_path) >= DISP_PATH_LEN:
            displayed_path = get_cropped_path(displayed_path)

        # update label with src path
        src_label.config(text=displayed_path)
        #before_label.config(text="before")

        # update labels with file counts in src pre sorting
        total, processable = count_folder(root_src_dir)
        files_in_src_before = total
        files_in_src_before_label.config(text=f"{total} files")

        pb_max = total # setter max_verdi for progressbar
        progress_bar.config(max=total)
        print2(f"progressbar max is set to {progress_bar['max']}")
    else:
        print2("User canceld file selection for src")
def set_dst_folder():
    """ Lets user set the destination folder usning a file chooser """
    global root_dst_dir, run_label, failed_destination

    if failed_destination:
        run_label['text'] = ""

    folderpath = filedialog.askdirectory()
    if folderpath:
        root_dst_dir = folderpath
        displayed_path = folderpath

        if len(displayed_path) >= DISP_PATH_LEN:
            displayed_path = get_cropped_path(displayed_path)

        dst_label.config(text=displayed_path)

        total, processable = count_folder(root_dst_dir)
        files_in_dst_before_label.config(text=f"{total} files")
    else:
        print("User canceld file selection for dst")
def run():
    """ Checks that everything is set up correctly before the process of sorting and moving images is started """
    global root_src_dir, root_dst_dir, progress_bar
    global src_button, dst_button, root, running_flag, failed_source, failed_destination


    src = root_src_dir
    if not src:
        run_label.config(text="provide a source")
        failed_source = True
        return
    if not os.path.isdir(src):
        run_label.config(text="source is not a valid directory")
        failed_source = True
        return

    # Ensure directory folder is placed before runing
    dst = root_dst_dir
    if not dst:
        run_label.config(text="provide a destination")
        failed_destination = True
        return
    if not os.path.isdir(dst):
        run_label.config(text="destination is not a valid directory")
        failed_destination = True
        return

    if files_in_src_before == 0:
        print("source is empty")
        src_label.config(text="Empty folder, can't be processed")
        return

    run_label.config(text="processing")
    running_flag = True
    program_loop()
    root.after_cancel(current_scheduled_update)
    progress_label.config(text="100 %")
    progress_bar['value'] = pb_max
    running_flag = False


    if not close_requested_flag:
        run_label.config(text="operation finished successfully")

    files_moved.config(text=f"{counter_files_moved} files moved")

    # count files for after labels
    tot, acp = count_folder(root_src_dir)
    files_in_src_after_label.config(text=f"{tot} files")
    tot, acp = count_folder(root_dst_dir)
    files_in_dst_after_label.config(text=f"{tot} files")


    src_button.config(state=tk.DISABLED)
    dst_button.config(state=tk.DISABLED)
    run_button.config(state=tk.DISABLED)
def program_loop():
    """ Will sort and move images """
    progress_label.config(text="0 %")
    update_pb4()    # start update_function. vil schedules seg selv til den er ferdig
    global counter_files_moved, move_processed_files, root, counter_files_counted, current_scheduled_update, run_label
    for dirpath, dirnames, filenames in walk(root_src_dir):
        for filename in filenames:

            if close_requested_flag:
                try:
                    print(f"<{root.tk.call('after', 'info')}>")
                    root.after_cancel(current_scheduled_update)
                    run_label.config(text="Execution stopped by user, press again to exit")
                    return
                except Exception as e:
                    # force
                    print(f"exception trying to close app, forcing shutdown")
                    print(f"exception:\n {e}")
                    exit(0)

            root.update_idletasks() # to not halt the GUI mainloop/eventloop
            root.update()           # to not halt
            counter_files_counted += 1

            # FILTER IMAGEFILE
            if not accepted_file(filename):
                continue


            # IMAGE
            image = path.join(dirpath, filename)

            # DATE
            date = get_date_taken(image)
            if date:
                month_name = calendar.month_name[date.month]
            else:
                continue

            # DST EXISTS?
            year = str(date.year)
            month =  str(date.month).zfill(2) + " " + month_name


            if "Screenshot" in filename:
                dst_dir = path.join(root_dst_dir, "screenshots", year, month)
            else:
                dst_dir = path.join(root_dst_dir, year, month)

            if not path.exists(dst_dir):
                makedirs(dst_dir)

            # NEW IMAGE
            new_image = path.join(dst_dir, filename)

            # NEW IMAGE EXISTS?
            if path.exists(new_image):
                i = 1
                while path.exists(new_image):
                    name, ext = path.splitext(filename)
                    new_image = path.join(dst_dir, f"{name}_{i}{ext}")
                    i += 1
            if close_requested_flag:
                print("wtf not closing")
            # MOVE
            if move_processed_files:
                shutil.move(image, new_image)
                counter_files_moved += 1
def update_pb4():
    """ Keeps track of the progress and updates the progressbar and % accordingly """

    global progress_bar, counter_files_counted, accumulated_progress, close_requested_flag, current_scheduled_update

    #~~~~~~~~~~~~~ PERCENTAGE
    # calculate the percentage
    # zero the file counter
    prosentfaktor = counter_files_counted / files_in_src_before
    prosent = prosentfaktor * 100   # viktig å bevare nøyaktigheten

    # if last update
    #   set progress label 100%
    if (100 - (prosent + accumulated_progress)) <= 0.01:
        print("siste update av progress")
        progress_label.config(text="100 %")
        progress_bar['value'] = (pb_max-1)

    # normal update
    #   incr progress label x %
    else:
        print(f"accum progress: {accumulated_progress}")
        accumulated_progress += prosent
        display_prosent = round(accumulated_progress)
        progress_label.config(text=f"{display_prosent} %")

        progress_bar.step(counter_files_counted)
        current_scheduled_update = root.after(SCHD_TIME, update_pb4)

        counter_files_counted = 0
        print(f"new accum progress: {accumulated_progress}")



# ~~~~~~~~~~~~~~~~~~~~~~~~
#         WINDOW
# ~~~~~~~~~~~~~~~~~~~~~~~~

root = tk.Tk()
root.title("Coherent"+" "*115 + "Sorter bilder")
#root.minsize(830, 250)  # width, height
root.resizable(False,False)
root.config(background="lightgrey")
root.protocol("WM_DELETE_WINDOW", close_requested)
root.iconbitmap(coherent_icon)

# ~~~~~~~~~~~~~~~~~~~~~~~~
#      PROGRESS BAR
# ~~~~~~~~~~~~~~~~~~~~~~~~

s = ttk.Style()
s.theme_use('clam')
s.configure("4.Horizontal.TProgressbar", troughcolor ='white', background="#0A83C5")
progress_bar = ttk.Progressbar(
    root,
    length=502,
    style="4.Horizontal.TProgressbar",
    mode="determinate",
    orient="horizontal"
)

# ~~~~~~~~~~~~~~~~~~~~~~~~
#         BUTTONS
# ~~~~~~~~~~~~~~~~~~~~~~~~

button_light_blue_background = "#0A83C5"
button_white_forground = "white"
button_font_name = "Helvetica"
button_font_size = 11
button_width = 19
button_height = 2
button_border = 1

src_button  = tk.Button(
    root,
    text="Source folder",
    command=set_src_folder,
    border=button_border,
    width=button_width,
    height=button_height,
    background=button_light_blue_background,
    foreground=button_white_forground,
    font=(button_font_name, button_font_size)
)

dst_button  = tk.Button(
    root,
    text="Destination folder",
    command=set_dst_folder,
    border=button_border,
    width=button_width,
    height=button_height,
    background=button_light_blue_background,
    foreground=button_white_forground,
    font=(button_font_name, button_font_size)
)

run_button  = tk.Button(
    root,
    text="Run",
    command=run,
    border=button_border,
    width=button_width,
    height=button_height,
    background=button_light_blue_background,
    foreground=button_white_forground,
    font=(button_font_name, button_font_size)
)

help_button = tk.Button(
    root,
    text="Help",
    command=help_window,
    border=button_border,
    width=button_width,
    height=button_height,
    background="lightgrey",
    foreground="black",
    font=(button_font_name, button_font_size)
)

# ~~~~~~~~~~~~~~~~~~~~~~~~
#         LABELS
# ~~~~~~~~~~~~~~~~~~~~~~~~

label_background = "#d1d1d1"

src_label = tk.Label(
    text="",
    font=(button_font_name, 12),
    width= 55,
    background=label_background
)

dst_label = tk.Label(
    text="",
    font=(button_font_name, 12),
    width= 55,
    background=label_background
)

run_label = tk.Label(
    text="",
    font=(button_font_name, 12),
    width= 55,
    background=label_background
)

progress_label = tk.Label(
    text="",
    font=(button_font_name, 12),
    background=label_background
)

phrase_label = tk.Label(
    text="\"Din foretrukne IT-partner - Skreddersydde løsninger for din bedrift\"",
    font=(button_font_name, 8),
    background=label_background
)

files_in_src_before_label = tk.Label(
    text="",
    font=(button_font_name, 10),
    width=10,
    anchor="w",
    background=label_background
)

files_in_src_after_label = tk.Label(
    text="",
    font=(button_font_name, 10),
    width=10,
    anchor="w",
    background=label_background
)

files_in_dst_before_label = tk.Label(
    text="",
    font=(button_font_name, 10),
    width=10,
    anchor="w",
    background=label_background
)

files_in_dst_after_label = tk.Label(
    text="",
    font=(button_font_name, 10),
    width=10,
    anchor="w",
    background=label_background
)

files_moved = tk.Label(
    text="",
    font=(button_font_name, 10),
    width=16,
    anchor="w",
    background=label_background
)

before_label = tk.Label(
    text="Before:",
    font=(button_font_name, 10),
    width=10,
    anchor="w",
    background=label_background
)

after_label = tk.Label(
    text="After:",
    font=(button_font_name, 10),
    width=10,
    anchor="w",
    background=label_background
)

# ~~~~~~~~~~~~~~~~~~~~~~~~
#         LAYOUT
# ~~~~~~~~~~~~~~~~~~~~~~~~

# colum  (0)
src_button.grid( row=1, column=0, padx=(15, 15))
dst_button.grid( row=2, column=0)
run_button.grid( row=3, column=0)
help_button.grid(row=4, column=0)

# colum  (1)

tk.ttk.Separator(root, orient=VERTICAL).grid(row=0, column=1, sticky='ns', rowspan=6)

# column (2)

src_label.grid(   row=1, column=2, padx=(15, 5))
dst_label.grid(   row=2, column=2, padx=(15, 5))
run_label.grid(   row=3, column=2, padx=(15, 5))
progress_bar.grid(row=4, column=2, padx=(15, 15))
phrase_label.grid(row=5, column=2, padx=(15, 15), pady=(15,15))

# column (3)

tk.ttk.Separator(root, orient=VERTICAL).grid(column=3, row=0, rowspan=6, sticky='ns')

# column (4)

before_label.grid(             row=0, column=4, padx=(15,5), pady=(15,0), sticky="w")
files_in_src_before_label.grid(row=1, column=4, padx=(15,5),              sticky="w")
files_in_dst_before_label.grid(row=2, column=4, padx=(15,5),              sticky="w")
files_moved.grid(              row=3, column=4, padx=(15,5),              sticky="w",    columnspan=2)
progress_label.grid(           row=4, column=4, padx=(15,5),              sticky="w")

# column  (5)

after_label.grid(              row=0, column=5, padx=(5,15), pady=(15,0),sticky="w")
files_in_src_after_label.grid( row=1, column=5, padx=(5,5),              sticky="w")
files_in_dst_after_label.grid( row=2, column=5, padx=(5,5),              sticky="w")



root.mainloop()


#    === END ===








