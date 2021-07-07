import csv, sqlite3, re, sys
import commands
from functools import reduce

# SQLite Database class
class SQLiteDB:
  def __init__(self, file_name):
    self.connection = sqlite3.connect(file_name)
    self.tables = {}

  def __del__(self):
    self.connection.close()

  # add DB table
  def add_table(self, name, descr, extra = ()):
    (field_list, field_dict) = descr
    if name in self.tables: raise Exception('table is already added: "' + name + '"')

    # create DB table
    table_descr = []
    for field in field_list: table_descr.append('"%s" %s' % (field, field_dict[field]))
    for item in extra: table_descr.append('"%s" %s' % (item[0], item[1]))
    stm = 'CREATE TABLE ' + name + ' (%s)' % ', '.join(table_descr)
    cursor = self.connection.cursor()
    cursor.execute(stm)
    self.connection.commit()

    # register table
    fields_str = ','.join(map(lambda x: '"' + x + '"', field_list))
    templ_str = ','.join('?' * len(field_list))
    stm = 'INSERT INTO ' + name + '(' + fields_str + ') VALUES(' + templ_str + ');'
    self.tables[name] = stm

    return (cursor, stm);

  # add columns to table
  def add_columns(self, name, columns):
    cursor = self.connection.cursor()
    for item in columns:
      stm = 'ALTER TABLE ' + name + ' ADD COLUMN "%s" %s' % (item[0], item[1])
      cursor.execute(stm)
    self.connection.commit()

  # add columns with expression
  def add_data_column(self, table_name, data_label, data_type, data_expr):
    cursor = self.connection.cursor()
    cursor.execute('ALTER TABLE %s ADD COLUMN "%s" %s' % (table_name, data_label, data_type))
    cursor.execute('UPDATE %s SET %s = (%s);' % (table_name, data_label, data_expr))

  # populate DB table entry
  def insert_entry(self, table, val_list):
    (cursor, stm) = table
    cursor.execute(stm, val_list)

  # populate DB table entry
  def commit_entry(self, table, val_list):
    self.insert_entry(table, val_list)
    self.connection.commit()

  # populate DB table data
  def insert_table(self, table, reader):
    for val_list in reader:
      if not val_list[-1]: val_list.pop()
      self.insert_entry(table, val_list)
    self.connection.commit()

  # return table fields list
  def _get_fields(self, table_name):
    cursor = self.connection.execute('SELECT * FROM ' + table_name)
    return list(map(lambda x: '"%s"' % (x[0]), cursor.description))

  # return table raws list
  def _get_raws(self, table_name):
    cursor = self.connection.execute('SELECT * FROM ' + table_name)
    return cursor.fetchall()
  def _get_raws_indexed(self, table_name):
    cursor = self.connection.execute('SELECT * FROM ' + table_name + ' order by "Index" asc;')
    return cursor.fetchall()
  def _get_raw_by_id(self, table_name, req_id):
    cursor = self.connection.execute('SELECT * FROM ' + table_name + ' WHERE "Index"=?', (req_id,))
    raws = cursor.fetchall()
    if len(raws) != 1:
      raise Exception('Index is not unique, table "' + table_name + '"')
    return list(raws[0])

  def table_get_rows(self, table_name):
    return self._get_raws(table_name)

  # execute query on DB
  def execute(self, cmd):
    cursor = self.connection.cursor()
    cursor.execute(cmd)

  # commit DB
  def commit(self):
    self.connection.commit()

  # close DB
  def close(self):
    self.connection.close()

  # access DB
  def get_raws(self, table_name):
    cur = self.connection.cursor()
    cur.execute("SELECT * FROM %s" % table_name)
    return cur.fetchall()

  # return CSV descriptor
  # list of fields and dictionaly for the fields types
  def _get_csv_descr(self, table_name, fd):
    reader = csv.DictReader(fd)
    field_names = reader.fieldnames
    if not field_names[-1]: field_names.pop()
    field_types = {}

    for entry in reader:
      fields_left = [f for f in field_names if f not in field_types.keys()]
      # all fields processed
      if not fields_left: break

      for field in fields_left:
          data = entry[field]
          # need data for the field to be processed
          if len(data) == 0: continue

          if data.isdigit():
              field_types[field] = "INTEGER"
          else:
              field_types[field] = "TEXT"

    if len(fields_left) > 0: raise Exception('types not found for fields: ', fields_left)
    return (field_names, field_types)

##############################################################################################
