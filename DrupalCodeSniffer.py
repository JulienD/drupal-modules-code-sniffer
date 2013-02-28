import MySQLdb
import os
from subprocess import Popen, PIPE
from shutil import rmtree

from xml.dom import minidom


class DrupalCodeSniffer:

	def __init__(self):	
		self.reports_path = os.path.expanduser('~') + '/drupal_code_sniffer_reports/reports'
		if not os.path.exists(self.reports_path):
			os.makedirs(self.reports_path)

		self.connection = MySQLdb.connect('localhost', 'root', 'password', 'drupalmodules')
		self.cursor =  self.connection.cursor()

	def __del__(self):
		self.connection.close()
		self.cursor.close()

	def parse(self):
		self.cursor.execute("""SELECT name, git_url, version FROM modules""")		
		numrows = int(self.cursor.rowcount)
		for i in range(numrows):			
			(name, git_url, version) = self.cursor.fetchone()
			self.sniff(name, git_url, version)			
		
	def sniff(self, name, git_url, version):
		project_path = '/tmp/Drupal_CodeSniffer/project'
		report_file = "%s/%s" % (self.reports_path, name)

		# Clone the project
		branch = "7.x-%s.x" % (version)		
		cmd = ["git clone %s --recursive --branch %s %s/%s" % (git_url, branch, project_path, name)]
		res = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).wait()
		#print res.stdout.read()
	
		# Run PHP_CodeSniffer with Drupal standard through the project.
		#cmd = "phpcs --standard=Drupal --extensions=php,module,inc,install,test,profile,theme,css,js,txt,info  --report=full --report-file=%s.txt %s/%s" % (report_file, project_path, name)
		#print cmd
		#res = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
		#res.wait()
		#print res.stdout.read()
		
		cmd = "phpcs --standard=Drupal --extensions=php,module,inc,install,test,profile,theme,css,js,txt,info -d error_reporting=0 --report=full %s/%s" % (project_path, name)
		full = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)

		cmd = "phpcs --standard=Drupal --extensions=php,module,inc,install,test,profile,theme,css,js,txt,info -d error_reporting=0 --report=summary %s/%s" % (project_path, name)
		source = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)

		#cmd = "phpcs --standard=Drupal --extensions=php,module,inc,install,test,profile,theme,css,js,txt,info  --report=summary --report-file=%s.txt %s/%s" % (report_file, project_path, name)		
		cmd = "phpcs --standard=Drupal --extensions=php,module,inc,install,test,profile,theme,css,js,txt,info -d error_reporting=0 --report=xml %s/%s" % (project_path, name)
		xml = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
		xml = xml.stdout.read()		
		(error, warning) = self.xmlReportAnalysis(xml)

		print ("%s >> error %s  - warning %s") % (name, error, warning)

		
		#rmtree("%s/%s") % (project_path, name)


	def xmlReportAnalysis(self, xml):
		error = warning = 0

		doc = minidom.parseString(xml)
		for node in doc.getElementsByTagName("file"):
			error = error + int(node.getAttribute("errors"))
			warning = warning + int(node.getAttribute("warnings"))

		return (error, warning)	
		#rmtree(project_path)		




DrupalCodeSniffer().parse()
