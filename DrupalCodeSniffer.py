import MySQLdb
import os
from subprocess import Popen, PIPE
from shutil import rmtree
from xml.dom import minidom
from string import split

class DrupalCodeSniffer:

	# Version of the Drupal module to fetch.
	version = ''

	# Current module_id.
	module_id = ''

	# Current module name.
	module_name = ''

	# Current module git url.
	module_git_url = ''

	# Current module branch.
	branch = ''

	# Path where the module is on the local machine.
	module_path = ''

	def __init__(self, version = '7'):
		self.version = '%s.x' % (version)
		self.connection = MySQLdb.connect('localhost', 'root', 'password', 'drupalmodules')

	def __del__(self):
		self.connection.close()

	# Parse a module to generate a PHP_CodeSniffer report for every valid branches.
	def parse(self):
		cursor = self.connection.cursor()
		#cursor.execute("""SELECT id, name, git_url, exclude FROM modules WHERE name LIKE 'commerce_%' """)
		cursor.execute("""SELECT id, name, git_url, exclude FROM modules""")

		# / ! \ have a look to the plato_tipico module.

		numrows = int(cursor.rowcount)
		for i in range(numrows):
			(self.module_id, self.module_name, self.module_git_url, exclude) = cursor.fetchone()

			if not(exclude):

				self.module_path = '/tmp/Drupal_CodeSniffer/project/%s' % (self.module_name)

				print ("%s") % (self.module_name)

				# Download the module if it doens't exist
				self.moduleDownload()

				branches = self.moduleGetBranches()

				# For each valid branch run the code throught PHP_CodeSniffer.
				for branch in branches:

					#
					self.branch = branch

					cursor_report = self.connection.cursor()
					cursor_report.execute("""SELECT commit_hash FROM reports WHERE module_id = %s AND branch = %s ORDER BY created DESC LIMIT 1""", (self.module_id, branch))
					report_commit_hash = cursor_report.fetchone()

					# Checkout the current branch.
					module_info = self.moduleUpdate()

					if not(report_commit_hash) or (module_info['commit_hash'] != report_commit_hash[0]):

						# Run the code throught the Drupal code sniffer.
						report = self.sniff()
						report['commit_hash'] = module_info['commit_hash']
						report['commit_date'] = module_info['commit_date']

						# Save the report in the database.
						self.saveReport(report)

						# Print debug info to the console.
						# @TODO : have a look on log().

						print " > branch %s : %i error(s) and %i warning(s) found" % (self.branch, report['error'], report['warning'])
					else:
						print ' > branch %s : nothing to do' % (self.branch)

		cursor.close()


	def moduleDownload(self):
		# Clone the project
		cmd = "git clone %s --recursive %s" % (self.module_git_url, self.module_path)
		Popen([cmd], shell=True, stdout=PIPE, stderr=PIPE).wait()


	def moduleUpdate(self):
		# Get the desired branch.
		Popen(["git --git-dir=%s/.git --work-tree=%s checkout %s" % (self.module_path, self.module_path, self.branch)], shell=True, stdout=PIPE, stderr=PIPE).wait()
		# Update the code repository
		#Popen(["git --git-dir=%s/.git pull" % (self.module_path)], shell=True, stdout=PIPE, stderr=PIPE)

		commit_hash = Popen(["git --git-dir=%s/.git --work-tree=%s log --format=format:'%%h' --date=relative -1" % (self.module_path, self.module_path)], shell=True, stdout=PIPE, stderr=PIPE)
		commit_date = Popen(["git --git-dir=%s/.git --work-tree=%s log --format=format:'%%ai' --date=relative -1" % (self.module_path, self.module_path)], shell=True, stdout=PIPE, stderr=PIPE)

		commit = {}
		commit['commit_hash'] = commit_hash.stdout.readlines()[0]
		commit['commit_date'] = commit_date.stdout.readlines()[0]

		return commit


	def moduleGetBranches(self):
		branches = []
		cmd = ["git --git-dir=%s/.git branch -a" % (self.module_path)]
		res = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)

		# Find in all branch a X.x version
		for branch in res.stdout.readlines():
			# Get the branch full name, split the full name to get the shortname,
			# remove '\n' and save it to a list.
			name = split(branch, '/')[-1].rstrip('\n')
			if name.startswith(self.version):
				branches.append(name)

		return list(set(branches))

	def sniff(self):
		xml = self.snifferGetReport('xml')
		(error, warning) = self.xmlReportAnalysis(xml)

		report = {}
		report['error']   = error
		report['warning'] = warning
		report['summary'] = self.snifferGetReport('summary')
		report['full']    = self.snifferGetReport('full')
		report['source']  = self.snifferGetReport('source')

		return report

	def snifferGetReport(self, report_type):

		print "Generating %s report"  % (report_type)
#		cmd = "phpcs --standard=Drupal --extensions=php,module,inc,install,test,profile,theme,css,js,txt,info -d error_reporting=0 --report=%s %s" % (report_type, self.module_path)
		cmd = "phpcs --standard=Drupal --extensions=module,inc,install,test,profile,theme,css,js,txt,info -d error_reporting=0 --report=%s %s" % (report_type, self.module_path)
		#print cmd
		process = Popen(cmd,
    	bufsize=-1,
      stdin=PIPE,
	    stdout=PIPE,
  	  stderr=PIPE,
      shell=True,
      cwd=os.curdir,
      env=os.environ)
		return process.stdout.read()

	def xmlReportAnalysis(self, xml):
		error = warning = 0
		doc = minidom.parseString(xml)
		xmlfile = doc.getElementsByTagName("file")
		if xmlfile:
			for node in xmlfile:
				error = error + int(node.getAttribute("errors"))
				warning = warning + int(node.getAttribute("warnings"))

		return (error, warning)

	def saveReport(self, report):
		cursor = self.connection.cursor()
		cursor.execute("""INSERT INTO reports (module_id, branch, commit_hash, commit_date, error, warning, summary, report, source) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
			(self.module_id,
			self.branch,
			report['commit_hash'],
			report['commit_date'],
			report['error'],
			report['warning'],
			report['summary'],
			report['full'],
			report['source'],
		))
		cursor.close()
		self.connection.commit()

DrupalCodeSniffer().parse()
