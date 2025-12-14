import pandas as pd #need for dictionary to CSV export


#Records outpiut to CSV, path is csv file to save to
def export_record_list(records, path):
    df = pd.DataFrame([r.to_dictionary() for r in records])  #will loop through each 'record' object in list r, converting them to dictionaries, then converts all to a DataFramn at once
    df.to_csv(path, index = False) #DataFram is exported to csv

