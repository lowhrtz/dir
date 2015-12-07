import os
from urlparse import parse_qs

# Change this if the WSGIScripAlias points to something other than "/dir"
BASE_URL_DIRECTORY = '/dir'

# If the voicemail.conf file is in a non-standard location then change this to reflect it
VM_CONFIG = '/etc/asterisk/voicemail.conf'

# The location of the directory where the Polycom directory files are kept
CONTACTS_DIR = '/tftpboot/contacts'

# MySQL settings
MYSQL_HOST = 'localhost'
MYSQL_USER = 'someuser'
MYSQL_PASS = 'somepass'
MYSQL_DB = 'asterisk'  # Change this if you created a MySQL/MariaDB Database under a different name.

########################################################################################################################

BASE_URL_DIRECTORY = BASE_URL_DIRECTORY.strip('/')


def get_index():
    """
    Generates the contents for the main page.

    :return: String containing the contents for the main page
    """

    string_template = {'base_dir': BASE_URL_DIRECTORY}
    return '''\
<head>
  <title>Directory Editor</title>
  <link rel="stylesheet" type="text/css" href="/{base_dir}/style.css">
</head>

<body class="auth">
Polycom Directory Editor<br />
  <form name="auth" id="auth" action="/{base_dir}/edit" method="post">

Extension: <input id="exten" type="text" name="exten"><br />
Password: &nbsp;<input id="pwd" type="password" name="pwd"><br /><br />
<input type="submit" value="Submit">

  </form>
</body>'''.format(**string_template)


def get_style():
    """
    Generates the CSS file contents.

    :return: String containing the contents of the stylesheet
    """

    return '''\
body {
text-align: center;
font: 50px Georgia, serif;
background: tan;
}

.wrap {
width: 950px;
margin-left: auto;
margin-right: auto;
}

.group-shell {
margin: 30px auto 40px;
font-size: 25px;
float: left;
}

.group {
padding: 5px;
background: lightblue;
border: 2px solid darkblue;
border-radius: 5px;
width: 400px;
margin: 20px 30px auto;
font-size: 20px;
box-shadow: 10px 10px 5px #888888;
}

.item {
background: #00FFBB;
padding: 2px 5px;
border: 1px solid brown;
border-radius: 5px;
margin: 5px;
}

.highlight {
border: 1px solid red;
background-color: #333333;
height: 34px;
margin: 5px;
}

.submit_dir {
margin-top: 30px;
font-size: 20px;
}

#auth {
background: lightblue;
padding: 10px;
width: 400px;
margin: 30px auto auto;
border: 3px ridge #555555;
border-radius: 15px;
box-shadow: 10px 10px 5px #888888;
font-size: 18px;
}

#exten {
margin-bottom: 3px;
}

#pwd {
margin-top: 3px;
}'''


def get_edit(exten, pwd):
    """
    Generates the contents for the edit page.

    :param exten: Extension as a string
    :param pwd: Voicemail password for the given extension
    :return: String containing the contents of the edit page
    """

    try:
        vm_config = open(VM_CONFIG, 'r')
    except IOError:
        return 'The file, voicemail.cfg, is missing or in an unexpected location.'

    no_user = True
    for line in vm_config:
        if line.startswith(exten + ' =>'):
            i = line.find('=>')
            i2 = line.find(',')
            beg_pass = i+2
            end_pass = i2
            actual_pwd = line[beg_pass:end_pass].strip()
            no_user = False
            break

    if no_user or pwd != actual_pwd:
        string_template = {'base_dir': BASE_URL_DIRECTORY}
        return '''\
<body style="background: tan;text-align: center;color: tan;"><span style="font-size: 35px;color: black;">Extension does not exist or password does not match.</span><br />
<a href="/{base_dir}" style="font-size: 25px;color: black;">back to login page</a></body>'''.format(**string_template)

    import MySQLdb as mysql
    import xml.etree.ElementTree as ET
    from xml.parsers.expat import ExpatError

    db = mysql.connect(host=MYSQL_HOST,
                       user=MYSQL_USER,
                       passwd=MYSQL_PASS,
                       db=MYSQL_DB)

    db_cursor = db.cursor()

    db_cursor.execute("SELECT * FROM endpointman_line_list WHERE ext='" + exten + "'")
    macid_rec = db_cursor.fetchone()
    try:
        macid = macid_rec[1]
    except IndexError:
        string_template = {'base_dir': BASE_URL_DIRECTORY}
        return '''\
<body style="background: tan;text-align: center;color: tan;"><span style="font-size: 35px;color: black;">Extension is not associated with a phone.</span><br />
<a href="/{base_dir}" style="font-size: 25px;color: black;">back to login page</a></body>'''.format(**string_template)

    db_cursor.execute("SELECT * FROM endpointman_mac_list WHERE id='" + str(macid) + "'")
    mac_rec = db_cursor.fetchone()
    mac = mac_rec[1]
    mac = mac.lower()

    error_to_print = ''
    dir_filename = mac + '-directory.xml'
    dir_fullpath = os.path.join(CONTACTS_DIR, dir_filename)
    try:
        tree = ET.parse(dir_fullpath)
        root = tree.getroot()
    except IOError:
        root = ET.fromstring('<directory></directory>')
    except ExpatError, ex:
        string_template = {'mac': mac}
        error_to_print = '''\
<span style="color: #F22424; font-size: 50%">There is a formatting problem with the XML directory file.<br />
A manual inspection of {mac}-directory.xml is probably needed.<br />
</span>'''.format(**string_template)
        root = ET.fromstring('<directory></directory>')

    string_template = {'base_dir': BASE_URL_DIRECTORY, 'dir_fullpath': dir_fullpath}
    html_string = '''\
<!DOCTYPE html>
<html>
  <head>
    <title>Edit Directory</title>
    <script src="https://code.jquery.com/jquery-1.11.1.js"></script>
    <script src="https://code.jquery.com/ui/1.11.1/jquery-ui.js"></script>
    <script>
$(document).ready(function(){
  function getDir() {
    var entries_json = [];
    $("#dir > div").each(function(index, entry) {
      var sd = index + 1;
      var entry_html = $(entry).html();
      var name = entry_html.split("<br>")[0];
      var contact = entry_html.split("<br>")[1];
      var entry_json = new Object();
      entry_json.name = name;
      entry_json.sd = sd;
      entry_json.contact = contact;
      entries_json.push(entry_json);
    });
    //alert(JSON.stringify(entries_json));
    return entries_json;
  }
  
  $(".group").sortable({
   placeholder: "highlight",
   connectWith: ".group"
  });
  
  $("button.submit_dir").click(function(){
    $.post("/%(base_dir)s/submit_dir",
      {
        filename:"%(dir_fullpath)s",
        entries_json:JSON.stringify(getDir())
      },
    function(data,status) {
        alert("Successfully updated the directory file!");
    })
    .fail( function(xhr, textStatus, errorThrown) {
      alert("Error saving directory file: %(dir_fullpath)s\\nThis usually means the server doesn't have permissions to write/rewrite the file.");
    });
  });

  $("button.add_entry").click(function() {
    var name = "";
    var contact = "";
    while (name == "") {
      name = prompt("New Entry's Name");
      if (name == null) {
        return;
      }
    }
    while (contact == "" || !contact.match(/^[0-9]+$/i)) {
      contact = prompt("New Entry's Number/Extension");
      if (contact == null) {
        return;
      }
    }
    var new_div = document.createElement("div");
    new_div.innerHTML = name + "<br />" + contact;
    new_div.className = "item";
    document.getElementById("dir").appendChild(new_div);
  });
});
    </script>
''' % string_template  # It is easier to use the old style formatting rather than double all the braces in the string.

    string_template = {'base_dir':BASE_URL_DIRECTORY, 'error': error_to_print}
    html_string += '''\
    <link rel="stylesheet" type="text/css" href="/{base_dir}/style.css">
  </head>
<body>
{error}
Edit Directory
<br /><button class="submit_dir">Save Changes</button>
<div class="wrap">
<div class="group-shell">
Current/Edit Entries
<div class="group" id="dir">
'''.format(**string_template)

    current_name_list = []
    for item in root.findall('*/item'):
        fn = item.findtext('fn')
        ln = item.findtext('ln')
        if fn is None: fn = ''
        if ln is None: ln = ''
        ct = item.findtext('ct')
        full_name = fn + ' ' + ln
        current_name_list.append(full_name.strip())
        string_template = {
        'fn': fn,
        'ln': ln,
        'ct': ct
        }
        html_string += '''\
<div class="item">{fn} {ln}<br />{ct}</div>
'''.format(**string_template)

    html_string += '''\

</div>
<br /><button class="add_entry">Add New Entry</button>
</div>

<div class="group-shell">
Available Entries
<div class="group" id="avail">
'''

    db_cursor.execute("SELECT * FROM sip WHERE keyword='account'")
    for row in db_cursor.fetchall():
        row_id = row[0]
        account = row[2]
        if row_id != account: continue  # Typically if the row id and account values don't match then it is a trunk not an extension.
        db_cursor.execute("SELECT * FROM users WHERE extension='" + account + "'")
        user = db_cursor.fetchone()
        name = user[2]
        if name.strip() not in current_name_list:
            string_template = {'name': name, 'account': account}
            html_string += '''\
<div class="item">{name}<br />{account}</div>
'''.format(**string_template)

    html_string += '''\
</div>
</div>
</div>

<div class="result"></div>

</body>
</html>'''

    vm_config.close()

    return html_string


def update_dir_file(entries_json_text, filename):
    """
    Updates the given directory file with the given json data.

    :param entries_json_text: Json data from POST request by edit page
    :param filename: Directory filename
    :return: Status string to pass to start_response
    """

    import json

    try:
        output_file = open(filename, 'w')
    except IOError:
        return '500 Internal Server Error'

    entries_json = json.loads(entries_json_text)

    output_file.write('<?xml version="1.0" standalone="yes"?>\n')
    output_file.write('<directory>\n')
    output_file.write('  <item_list>\n')

    for entry in entries_json:
        sd = entry['sd']
        name = entry['name']
        name_split = name.split(None, 1)
        first_name = name_split[0]
        if len(name_split) > 1:
            last_name = name_split[1]
        else:
            last_name = ''
        contact = entry['contact']
        output_file.write('    <item>\n')
        output_file.write('      <fn>' + str(first_name) + '</fn>\n')
        output_file.write('      <ln>' + str(last_name) + '</ln>\n')
        output_file.write('      <ct>' + str(contact) + '</ct>\n')
        output_file.write('      <sd>' + str(sd) + '</sd>\n')
        output_file.write('      <rt>ringerdefault</rt>\n')
        output_file.write('      <pt>0</pt>\n')
        output_file.write('      <ad>0</ad>\n')
        output_file.write('      <ar>0</ar>\n')
        output_file.write('      <bw>1</bw>\n')
        output_file.write('      <bb>0</bb>\n')
        output_file.write('    </item>\n')

    output_file.write('  </item_list>\n')
    output_file.write('</directory>\n')
    output_file.close()
    return '201 Created'


def application(environ, start_response):
    """
    WSGI interface

    :param environ: Pertinent environment variables
    :param start_response: Function WSGI passes to let the script define headers and response codes
    :return: List of strings to send to the browser
    """
    status_OK = '200 OK'
    status_REDIRECT = '302 Found'

    response_header = [('Content-type','text/html')]

    request_uri = environ.get('REQUEST_URI', '')
    request_method = environ.get('REQUEST_METHOD', '')

    status = status_OK
    html_string = ''
    if request_uri.endswith(BASE_URL_DIRECTORY + '/style.css'):
        response_header = [('Content-type','text/css')]
        html_string = get_style()
    elif request_uri.endswith(BASE_URL_DIRECTORY + '/edit'):
        raw_post = environ.get('wsgi.input', '')
        post_input = parse_qs(raw_post.readline().decode(),True)
        exten = post_input.get('exten', [''])[0]
        pwd = post_input.get('pwd', [''])[0]
        if request_method == 'POST' and len(exten.strip()) > 0 and len(pwd.strip()) > 0:
            html_string = get_edit(exten, pwd)
        else:
            status = status_REDIRECT
            response_header = [('Location','/' + BASE_URL_DIRECTORY)]
    elif request_uri.endswith(BASE_URL_DIRECTORY + '/submit_dir'):
        raw_post = environ.get('wsgi.input', '')
        post_input = parse_qs(raw_post.readline().decode(),True)
        entries_json_text = post_input.get('entries_json', [''])[0]
        filename = post_input.get('filename', [''])[0]
        if request_method == 'POST' and filename != '':
            status = update_dir_file(entries_json_text, filename)
        else:
            status = status_REDIRECT
            response_header = [('Location','/' + BASE_URL_DIRECTORY)]
    elif request_uri.endswith(BASE_URL_DIRECTORY):
        html_string = get_index()
    else:
        status = status_REDIRECT
        response_header = [('Location','/' + BASE_URL_DIRECTORY)]

    start_response(status, response_header)
    return [html_string]

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    srv = make_server('localhost', 8080, application)
    srv.serve_forever()
