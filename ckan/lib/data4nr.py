import os.path

class Data4Nr(object):
    
    
    def load_csv_into_db(self, csv_filepath):
        assert os.path.exists(csv_filepath)
        f_obj = open(csv_filepath, "r")
        for line in f_obj.readline():
            data4nr_dict = self.parse_line(line)
            self.load_line_into_db(data4nr_dict)
