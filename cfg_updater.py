# -*- coding: utf-8 -*-
import os
import re
import json
import zipfile
import argparse # parse command line
import git # require GitPython 0.3.1 or later (pip install GitPython==0.3.1-beta2)
import shutil # remove a dictionary
import subprocess # run another process
import tempfile # cross plateform temp directory
import ftplib # upload zipfiles 

FTP_USERNAME = ''
FTP_PASSWORD = ''

def get_temp_folder(folder_name):
	temp_dir = os.path.join(tempfile.gettempdir(), folder_name)
	print 'using temp folder: ' + temp_dir
	if os.path.exists(temp_dir):
		shutil.rmtree(temp_dir)
	os.makedirs(temp_dir)
	return temp_dir

def enter_ftp_dir(ftp_client, ftp_dir):
    filelist = []
    ftp_client.retrlines('LIST',filelist.append)
    dir_exists = False
    for f in filelist:
        if f.split()[-1] == ftp_dir and f.upper().startswith('D'):
        	dir_exists = True
    if not dir_exists:
    	ftp_client.mkd(ftp_dir)
    	ftp_client.cwd(ftp_dir)

def get_zip_file_name(file_path):
	return '-'.join(re.split('\W+', file_path)) + '.zip'

def find_new_files_and_upload(from_ver, to_ver, repo_path, ftp_address, http_address, sub_path):
	new_file_list = []
	temp_dir = ''
	output_dict = {'from': from_ver, 'to': to_ver, 'A': [], 'D': []}
	try:
		# 解析repository
		repo = git.Repo(repo_path, odbt=git.GitCmdObjectDB)
		repo.remotes.origin.fetch()
		repo.git.checkout(to_ver)
		result = repo.git.diff('--name-status', from_ver, to_ver, sub_path)
		print result
		lines =  result.split('\n')
		for line in lines:
			word = line.split('\t')
			# currently 'R'(rename) is not considered
			if (word[0] == 'M' or word[0] == 'A'):
				new_file_list.append(word[1])
			elif(word[0] == 'D'):
				output_dict['D'].append(word[1])

		# 上传ftp
		ftp = ftplib.FTP()
		ftp.connect(ftp_address, 21)
		ftp.login(FTP_USERNAME, FTP_PASSWORD)
		enter_ftp_dir(ftp, to_ver)
		temp_dir = get_temp_folder(to_ver)
		for new_file in new_file_list:
			dest_dir = os.path.dirname(new_file)
			zipfile_name = get_zip_file_name(new_file)
			src_file = os.path.join(repo_path, new_file)
			dest_file = os.path.join(temp_dir, zipfile_name)
			with zipfile.ZipFile(dest_file, 'w') as zf:
				zf.write(src_file, arcname=new_file)
			with open(dest_file, 'rb') as zf:
				ftp.storbinary('STOR ' + zipfile_name, zf)
				print 'upload ' + zipfile_name
			path = http_address + '/' + to_ver + '/' + zipfile_name
			output_dict['A'].append({'name': new_file, 'path': path})
		ftp.quit()

		# 生成json文件
		with open ('output.json', 'wb') as fp:
			json.dump(output_dict, fp, indent=4, sort_keys=True)
		print 'generate output'
	finally:
		# 清理
		if os.path.exists(temp_dir):
			shutil.rmtree(temp_dir)
		repo.git.checkout('master')

def notify(cs_address, cs_port):
	cmd_name = ''
	if os.name == 'nt':
		cmd_name = 'VersionPublisher.exe'
	else:
		cmd_name = './VersionPublisher'
	subprocess.call([cmd_name, cs_address, cs_port])

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('repo', type=str, help='git repository path')
	parser.add_argument('-b', '--begin', type=str, help='begin version for comparing')
	parser.add_argument('-e', '--end', type=str, help='end version for comparing')
	parser.add_argument('-hs', '--httpserver', type=str, help='http server address')
	parser.add_argument('-fs', '--ftpserver', type=str, help='ftp server address')
	parser.add_argument('-c', '--controlserver', type=str, help='control server adress')
	parser.add_argument('-p', '--controlport', type=str, help= 'control server port')
	parser.add_argument('-sp', '--subpath', type=str, help='repository subpath for comparing')
	args = parser.parse_args()
	find_new_files_and_upload(args.begin, args.end, args.repo, args.ftpserver, args.httpserver, args.subpath)
	notify(args.controlserver, args.controlport)
