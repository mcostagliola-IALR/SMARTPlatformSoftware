import os
import sys
import pandas as pd
from natsort import natsorted
import customtkinter as ctk
import tkinter as tk  # for messagebox
import matplotlib
import scienceplots
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker # This can likely be removed if AutoDateLocator works well
#plt.style.use('ggplot')
matplotlib.use('Agg') # Use Agg backend for non-GUI environments

def get_excel_col(n):
    """Convert column index to Excel column label (1-indexed)."""
    name = ''
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        name = chr(65 + remainder) + name
    return name

class GroupWindow(ctk.CTkToplevel):
    def __init__(self, master, plants, current_groups, custom_groups, add_group_callback):
        super().__init__(master)
        self.title("Assign Plant Groups")
        self.geometry("400x500")
        self.resizable(True, True)
        self.grab_set()  # Modal window

        self.master = master # Keep a reference to the master for consistent styling
        self.plants = plants
        self.custom_groups = custom_groups
        self.add_group_callback = add_group_callback  # callback to notify main window on new group

        self.group_vars = {}  # plant_name -> ctk.StringVar

        # Scrollable frame for plants
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=380, height=400)
        self.scroll_frame.pack(padx=10, pady=(10, 0), fill="both", expand=True)

        # Add plants with group radio buttons
        self._populate_plants()

        # Entry + button to add new groups
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(pady=10, padx=10, fill='x')

        self.new_group_entry = ctk.CTkEntry(add_frame, placeholder_text="New Group Name")
        self.new_group_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        self.add_group_button = ctk.CTkButton(add_frame, text="Add Group", width=90, command=self.add_group)
        self.add_group_button.pack(side='right')

        # Close button
        close_btn = ctk.CTkButton(self, text="Done", command=self.on_close)
        close_btn.pack(pady=(0, 10))

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _populate_plants(self):
        # Clear existing widgets
        for child in self.scroll_frame.winfo_children():
            child.destroy()

        for plant_name in self.plants:
            inner_frame = ctk.CTkFrame(self.scroll_frame)
            inner_frame.pack(fill='x', padx=5, pady=3)

            label = ctk.CTkLabel(inner_frame, text=plant_name, width=90)
            label.pack(side='left', padx=(0, 10))

            # Get current selection or default to "Control"
            current_value = self.master.plant_groups.get(plant_name, "Control")
            group_var = ctk.StringVar(value=current_value)
            self.group_vars[plant_name] = group_var

            for group_name in self.custom_groups.keys():
                radio = ctk.CTkRadioButton(
                    master=inner_frame,
                    text=group_name,
                    variable=group_var,
                    value=group_name,
                )
                radio.pack(side='left', padx=3)

    def add_group(self):
        group_name = self.new_group_entry.get().strip()
        if not group_name:
            return
        if group_name in self.custom_groups:
            tk.messagebox.showinfo("Info", f"Group '{group_name}' already exists.")
            return

        self.add_group_callback(group_name)
        self.new_group_entry.delete(0, tk.END)
        self.refresh_groups()

    def refresh_groups(self):
        # Re-populate plants to include new groups as radio options
        self._populate_plants()

    def on_close(self):
        # Copy back selections to master.plant_groups
        for plant_name, var in self.group_vars.items():
            self.master.plant_groups[plant_name] = var.get()
            # print(f"Set {plant_name} to group: {var.get()}") # Debug print, can be removed
        self.destroy()

class ExcludePlantsWindow(ctk.CTkToplevel):
    def __init__(self, master, plants_list, excluded_plants_set):
        super().__init__(master)
        self.title("Exclude Plants from Plotting")
        self.geometry("350x450")
        self.resizable(True, True)
        self.grab_set()

        self.plants_list = plants_list
        self.excluded_plants_set = excluded_plants_set # Reference to master's set
        self.plant_checkbox_vars = {} # plant_name -> ctk.BooleanVar

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=330, height=380)
        self.scroll_frame.pack(padx=10, pady=(10, 0), fill="both", expand=True)

        # Instructions
        instruction_label = ctk.CTkLabel(self.scroll_frame, text="Uncheck plants to EXCLUDE them from plots:",
                                         font=ctk.CTkFont(weight="bold"))
        instruction_label.pack(pady=(5, 10))

        for plant_name in self.plants_list:
            # Checkbox state: True if NOT in excluded_plants_set, False if IN excluded_plants_set
            var = ctk.BooleanVar(value=(plant_name not in self.excluded_plants_set))
            self.plant_checkbox_vars[plant_name] = var
            checkbox = ctk.CTkCheckBox(self.scroll_frame, text=plant_name, variable=var)
            checkbox.pack(anchor='w', padx=5, pady=2)

        close_btn = ctk.CTkButton(self, text="Done", command=self.on_close)
        close_btn.pack(pady=(0, 10))

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        # Update the master's excluded_plants_set based on checkbox states
        self.excluded_plants_set.clear() # Clear existing exclusions
        for plant_name, var in self.plant_checkbox_vars.items():
            if not var.get(): # If checkbox is unchecked, it means exclude
                self.excluded_plants_set.add(plant_name)
        print(f"Plants excluded from plotting: {self.excluded_plants_set}")
        self.destroy()


class GUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.minsize(980, 540)
        self.resizable(width=False, height=False)
        self.title('Excel Merger for Plant Data')
        self._set_appearance_mode("system")

        self.path_var = ctk.StringVar()
        self.path_label = ctk.CTkLabel(self, text="Selected Folder Path:")
        self.path_label.place(x=30, y=10)

        self.path_entry = ctk.CTkEntry(self, textvariable=self.path_var, width=690,
                                         corner_radius=8, border_color='gray40', border_width=2)
        self.path_entry.place(x=160, y=10)

        self.debug_window = ctk.CTkTextbox(self, state='disabled',
                                             border_color='gray40', border_width=2,
                                             corner_radius=8, width=600, height=420)
        self.debug_window.place(x=250, y=60)

        sys.stdout = TextRedirector(self.debug_window, "stdout")
        sys.stderr = TextRedirector(self.debug_window, "stderr")

        self.choose_folder_button = ctk.CTkButton(self, text='Choose Folder', width=200, height=89,
                                                  corner_radius=8, command=self.getPath)
        self.choose_folder_button.place(x=30, y=60)

        self.preview_button = ctk.CTkButton(self, text='Preview Files', width=200, height=89,
                                             corner_radius=8, command=self.previewFiles)
        self.preview_button.place(x=30, y=160)

        self.assign_groups_button = ctk.CTkButton(self, text='Assign Groups', width=200, height=89,
                                                  corner_radius=8, command=self.open_group_window)
        self.assign_groups_button.place(x=30, y=260)

        self.merge_sheets_button = ctk.CTkButton(self, text='Merge Sheets', width=200, height=89,
                                                 corner_radius=8, command=self.mergeData)
        self.merge_sheets_button.place(x=30, y=360)

        self.legend = []
        self.plant_groups = {}
        # New: Set for plants to exclude from plotting
        self.excluded_plants = set() # Stores names of plants to be excluded from plots

        self.custom_groups = {
            "Control": "#3366CC",
            "Experimental": "#DC3912"
        }
        self.default_color_palette = [
            "#3366CC", "#DC3912", "#FF9900", "#109618",
            "#990099", "#0099C6", "#DD4477", "#66AA00"
        ]
        self.next_group_color_index = 2  # Already using first two colors

        self.group_legend_frame = ctk.CTkFrame(self, width=200, height=200, corner_radius=8)
        self.group_legend_frame.place(x=860, y=60)
        self.update_group_legend()

        # New: Matplotlib plot options
        self.plot_checkbox_var = ctk.BooleanVar(value=True) # Default to True
        self.plot_checkbox = ctk.CTkCheckBox(self, text="Generate Matplotlib Plots",
                                             variable=self.plot_checkbox_var,
                                             onvalue=True, offvalue=False)
        self.plot_checkbox.place(x=30, y=500) # Adjust position

        self.exclude_plants_button = ctk.CTkButton(self, text="Exclude Plants from Plots",
                                                   command=self.open_exclude_plants_window)
        self.exclude_plants_button.place(x=30, y=460) # Adjust position

    def update_group_legend(self):
        for widget in self.group_legend_frame.winfo_children():
            widget.destroy()

        title = ctk.CTkLabel(self.group_legend_frame, text="Group Legend", font=ctk.CTkFont(weight="bold"))
        title.pack(pady=(5, 10))

        for group_name, color in self.custom_groups.items():
            row = ctk.CTkFrame(self.group_legend_frame, fg_color="transparent")
            row.pack(fill='x', padx=5, pady=2)

            color_box = ctk.CTkLabel(row, text="", width=15, height=15, fg_color=color, corner_radius=2)
            color_box.pack(side="left", padx=(0, 10))

            label = ctk.CTkLabel(row, text=group_name)
            label.pack(side="left")

    def clear(self):
        self.debug_window.configure(state=ctk.NORMAL)
        self.debug_window.delete('1.0', ctk.END)
        self.debug_window.configure(state=ctk.DISABLED)
        self.debug_window.update_idletasks()

    def getPath(self):
        self.path_var.set("")
        self.path = ctk.filedialog.askdirectory()
        self.path_var.set(self.path)
        self.legend = []
        self.plant_groups = {}
        self.excluded_plants = set() # Reset exclusions when new folder is chosen

    def findAllExcelFiles(self, root_path):
        excel_files = []
        for root, _, files in os.walk(root_path):
            for file in files:
                if file.endswith(".xlsx") and not file.startswith("~$"):
                    excel_files.append(os.path.join(root, file))
        return natsorted(excel_files)

    def previewFiles(self):
        self.clear()
        path = self.path_var.get()
        if not path:
            print("Please select a folder first.")
            return
        files = self.findAllExcelFiles(path)
        if not files:
            print("No Excel files found.")
            return

        print(f"Found {len(files)} Excel files:\n")
        num_motion_files = sum(1 for f in files if 'motion_analysis_report.xlsx' in f)
        num_size_files = sum(1 for f in files if 'mask_sizes.xlsx' in f)

        num_plants = max(num_motion_files, num_size_files)
        # Ensure legend is updated to reflect all found plants
        new_legend = [f"Plant{i+1}" for i in range(num_plants)]
        
        # Only add new plants to groups, don't reset existing assignments
        for plant_name in new_legend:
            if plant_name not in self.plant_groups:
                self.plant_groups[plant_name] = "Control"
        self.legend = new_legend # Update the main legend list

        # Initialize excluded_plants based on previous state or default
        # If new plants are found, they are *not* excluded by default.
        # If plants are no longer found, their exclusion status will persist but won't be applied.
        
        for f in files:
            print(f)

        print("\nNow click 'Assign Groups' to assign groups to plants.")
        print("Click 'Exclude Plants from Plots' to select which plants to display.")


    def open_group_window(self):
        if not self.legend:
            tk.messagebox.showinfo("Info", "Please preview files first to detect plants.")
            return

        self.group_window = GroupWindow(
            master=self,
            plants=self.legend,
            current_groups=self.plant_groups,
            custom_groups=self.custom_groups,
            add_group_callback=self.add_custom_group
        )
        self.group_window.focus()

    def open_exclude_plants_window(self):
        if not self.legend:
            tk.messagebox.showinfo("Info", "Please preview files first to detect plants.")
            return
        
        # Pass a copy of legend and a reference to excluded_plants
        self.exclude_window = ExcludePlantsWindow(
            master=self,
            plants_list=self.legend,
            excluded_plants_set=self.excluded_plants
        )
        self.exclude_window.focus()


    def add_custom_group(self, group_name):
        if group_name in self.custom_groups:
            print(f"Group '{group_name}' already exists.")
            return

        color = self.default_color_palette[self.next_group_color_index % len(self.default_color_palette)]
        self.custom_groups[group_name] = color
        self.next_group_color_index += 1
        self.update_group_legend()
        print(f"Added custom group: {group_name} with color {color}")


    def mergeData(self):
        self.clear()
        path = self.path_var.get()
        if not path:
            print("Please select a folder first.")
            return

        os.chdir(path)
        excelFileList = self.findAllExcelFiles(path)
        if not excelFileList:
            print("No Excel files to merge.")
            return

        print("Merging the following Excel files:")
        for f in excelFileList:
            print(f)

        merged_df_Motion = pd.DataFrame()
        merged_df_Size = pd.DataFrame()
        all_time_motion_data = {}
        all_time_size_data = {}

        if not self.legend: # If previewFiles was not run, or no plants detected then initialize
            num_motion_files = sum(1 for f in excelFileList if 'motion_analysis_report.xlsx' in f)
            num_size_files = sum(1 for f in excelFileList if 'mask_sizes.xlsx' in f)
            num_plants = max(num_motion_files, num_size_files)
            self.legend = [f"Plant{i+1}" for i in range(num_plants)]
            for plant_name in self.legend:
                if plant_name not in self.plant_groups: # Only set if not already present
                    self.plant_groups[plant_name] = "Control"


        for file in excelFileList:
            print(f'Processing file: {file}')
            try:
                self.update()
                if 'motion_analysis_report.xlsx' in file:
                    dfM = pd.read_excel(file, sheet_name='Displacement Data', skiprows=[0], usecols='B')
                    merged_df_Motion = pd.concat([merged_df_Motion, dfM], axis=1)
                    time_df_motion = pd.read_excel(file, sheet_name='Displacement Data', skiprows=[0], usecols='A')
                    all_time_motion_data[file] = time_df_motion
                elif 'mask_sizes.xlsx' in file:
                    dfS = pd.read_excel(file, sheet_name='Sheet1', skiprows=[0], usecols='C')
                    merged_df_Size = pd.concat([merged_df_Size, dfS], axis=1)
                    time_df_size = pd.read_excel(file, sheet_name='Sheet1', skiprows=[0], usecols='A')
                    all_time_size_data[file] = time_df_size
            except Exception as e:
                print(f'Error processing {file}: {e}')
                tk.messagebox.showerror("Error", f"Error processing {os.path.basename(file)}:\n{e}")
                return

        rowM = merged_df_Motion.shape[0]
        rowS = merged_df_Size.shape[0]

        median_motion_time_df = pd.DataFrame()
        if all_time_motion_data:
            median_motion_file = natsorted(list(all_time_motion_data.keys()))[len(all_time_motion_data) // 2]
            median_motion_time_df = all_time_motion_data[median_motion_file]

        median_size_time_df = pd.DataFrame()
        if all_time_size_data:
            median_size_file = natsorted(list(all_time_size_data.keys()))[len(all_time_size_data) // 2]
            median_size_time_df = all_time_size_data[median_size_file]

        merged_motion_with_time = pd.concat([median_motion_time_df, merged_df_Motion], axis=1)
        merged_size_with_time = pd.concat([median_size_time_df, merged_df_Size], axis=1)

        # Update legend for export based on actual number of columns (plants)
        # It's important that this legend precisely matches the number of plant columns
        # created by pd.concat, regardless of previously detected 'num_plants'.
        # If more plants are found than initially previewed, this updates legend for Excel export.
        self.legend = [f"Plant{i+1}" for i in range(merged_df_Motion.shape[1])]
        # Ensure plant_groups has entries for all plants in the updated legend
        for plant_name in self.legend:
            if plant_name not in self.plant_groups:
                self.plant_groups[plant_name] = "Control" # Default new plants to 'Control'

        merged_motion_with_time.columns = ['Time'] + self.legend
        merged_size_with_time.columns = ['Time'] + self.legend

        # Generate Matplotlib Plots (ggplot style) with filtered plants only IF checkbox is checked
        if self.plot_checkbox_var.get():
            motion_chart_path = os.path.join(path, "motion_chart.png")
            size_chart_path = os.path.join(path, "size_chart.png")

            # Determine which plants to plot based on the excluded_plants set
            plot_plants_list = [plant for plant in self.legend if plant not in self.excluded_plants]
            
            if not plot_plants_list:
                print("No plants selected for plotting after exclusions. Skipping chart generation.")
            else:
                def plot_group_chart(df, y_label, title, save_path, plants_to_plot):
                    # Convert 'Time' column to datetime objects specifically for plotting
                    # Using .copy() to avoid SettingWithCopyWarning if original df is a slice
                    df_for_plot = df.copy()
                    df_for_plot['Time'] = pd.to_datetime(df_for_plot['Time'])

                    # Use SciencePlots style
                    with plt.style.context(['pgf', 'grid', 'science']): # Apply science and grid styles
                    
                        fig, ax = plt.subplots(figsize=(12, 7)) 
                        
                        # Store unique group labels and colors for a cleaner legend
                        plotted_groups = set()
                        
                        for plant in plants_to_plot:
                            group = self.plant_groups.get(plant, "Control")
                            color = self.custom_groups.get(group, "#000000")
                            
                            # Plot individual plant lines
                            ax.plot(df_for_plot["Time"], df_for_plot[plant],
                                        color=color, linewidth=1, alpha=0.7)
                            
                            # Add group label only once to the legend, using a "dummy" handle
                            if group not in plotted_groups:
                                ax.plot([], [], label=group, color=color, linewidth=2, alpha=1) # Dummy plot for legend
                                plotted_groups.add(group)

                        # Rebuild legend handles/labels to ensure only group names appear
                        handles, labels = ax.get_legend_handles_labels()
                        unique_labels_and_handles = dict(zip(labels, handles))
                        ax.legend(unique_labels_and_handles.values(), unique_labels_and_handles.keys(),
                                    title="Groups", loc='upper left', bbox_to_anchor=(1, 1),
                                    fontsize='small', title_fontsize='medium')
                        
                        # Adjust plot area to make space for the legend
                        fig.subplots_adjust(right=0.75) 

                        ax.set_title(title, fontsize=16, fontweight='bold', pad=20) 
                        ax.set_xlabel("Capture Date", fontsize=14, fontweight='bold', labelpad=10) 
                        ax.set_ylabel(y_label, fontsize=14, fontweight='bold', labelpad=10)

                        # SciencePlots handles grid automatically with 'grid' style
                        # ax.grid(True, which='major', linestyle='-', linewidth=0.7, color='gray') 
                        # ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='lightgray')
                        # ax.minorticks_on() 

                        plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=10)
                        plt.setp(ax.get_yticklabels(), fontsize=10)

                        # AutoDateLocator for intelligent date ticks
                        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y %H:%M'))
                        
                        # Try to set reasonable date intervals for minor ticks
                        ax.xaxis.set_minor_locator(mdates.AutoDateLocator(maxticks=10)) 

                        fig.tight_layout() 
                        fig.savefig(save_path, bbox_inches='tight', dpi=300) 
                        plt.close(fig)

                plot_group_chart(merged_motion_with_time, "Plant Displacement (px)", "Plant Motion Over Time", motion_chart_path, plot_plants_list)
                plot_group_chart(merged_size_with_time, "Pixel Count (px)", "Plant Size Over Time", size_chart_path, plot_plants_list)
                print("\nMatplotlib charts generated.")
        else:
            print("Skipping Matplotlib chart generation as per user setting.")


        try:
            with pd.ExcelWriter('Merged.xlsx', engine='xlsxwriter') as writer:
                merged_motion_with_time.to_excel(writer, sheet_name='Motion_Worksheet', index=False)
                merged_size_with_time.to_excel(writer, sheet_name='Size_Worksheet', index=False)

                workbook = writer.book
                worksheetMotion = writer.sheets['Motion_Worksheet']
                worksheetSize = writer.sheets['Size_Worksheet']

                # Excel Charts
                chartMotion = workbook.add_chart({'type': 'scatter', 'subtype': 'straight'})
                chartMotion.set_title({'name': 'Plant Motion Over Time', 'name_font': {'size': 18, 'bold': True}})
                chartMotion.set_x_axis(
                    {'name': 'Capture Date', 
                        'name_font': {'size': 14, 'bold': True},
                        'num_font': {'rotation': -45, 'size': 10},
                        'date_axis': True, 'major_unit': 0.6,
                        'num_format': 'mm/dd/yyyy HH:MM',
                        'interval_tick': 1}  # Adjust interval_tick for better density
                    ) # Adjust major_unit for better density
                chartMotion.set_y_axis({'name': 'Plant Displacement (px)', 'name_font': {'size': 14, 'bold': True}, 'num_font': {'size': 10}})
                chartMotion.set_legend({'position': 'right'}) # Place legend on the right

                chartSize = workbook.add_chart({'type': 'line'})
                chartSize.set_title({'name': 'Plant Size Over Time', 'name_font': {'size': 18, 'bold': True}})
                chartSize.set_x_axis(
                    {'name': 'Capture Date',
                        'name_font': {'size': 14, 'bold': True},
                        'num_font': {'rotation': -45, 'size': 10},
                        'date_axis': True, 'major_unit': 50,
                        'num_format': 'mm/dd/yyyy HH:MM',
                        'interval_tick' :60}
                    ) # Adjust major_unit for better density
                chartSize.set_y_axis({'name': 'Pixel Count (px)', 'name_font': {'size': 14, 'bold': True}, 'num_font': {'size': 10}})
                chartSize.set_legend({'position': 'right'}) # Place legend on the right


                # Iterate through all plants in self.legend (i.e., all plants in the Excel data)
                # and add series for the Excel charts.
                # Do NOT use plot_plants_list here, as Excel export should include all data.
                for i, plant_name in enumerate(self.legend):
                    col_letter = get_excel_col(i + 2) # +2 because A is Time, B is Plant1, C is Plant2 etc.
                    group = self.plant_groups.get(plant_name, "Control")
                    color = self.custom_groups.get(group, 'black')

                    chartMotion.add_series({
                        'name': f"{group} - {plant_name}",
                        'categories': f'=Motion_Worksheet!$A$2:$A${rowM+1}',
                        'values': f'=Motion_Worksheet!${col_letter}$2:${col_letter}${rowM+1}',
                        'line': {'color': color, 'width': 1},
                    })

                    chartSize.add_series({
                        'name': f"{group} - {plant_name}",
                        'categories': f'=Size_Worksheet!$A$2:$A${rowS+1}',
                        'values': f'=Size_Worksheet!${col_letter}$2:${col_letter}${rowS+1}',
                        'line': {'color': color, 'width': 1},
                    })

                worksheetMotion.insert_chart('F5', chartMotion, {'x_scale': 2.5, 'y_scale': 2})
                worksheetSize.insert_chart('F5', chartSize, {'x_scale': 2.5, 'y_scale': 2})


            print("\nMerged.xlsx created successfully.")
            tk.messagebox.showinfo("Success", "Merged.xlsx created successfully!")

        except Exception as e:
            print(f"Error creating Merged.xlsx: {e}")
            tk.messagebox.showerror("Error", f"Error creating Merged.xlsx:\n{e}")

class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, string):
        self.widget.configure(state=ctk.NORMAL)
        self.widget.insert(ctk.END, string, (self.tag,))
        self.widget.see(ctk.END)
        self.widget.configure(state=ctk.DISABLED)
        self.widget.update_idletasks()

app = GUI()
app.mainloop()