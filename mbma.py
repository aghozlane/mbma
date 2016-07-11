#! /usr/bin/env python
# -*- coding: utf8 -*-


__author__ = "Anita Annamalé"
__version__  = "1.0"
__copyright__ = "copyleft"
__date__ = "2016/02"

#-------------------------- MODULES IMPORTATION -------------------------------#

import sys
import os.path
from os import listdir
import argparse
import re
import subprocess
import shlex
import glob
import time
import shutil
import stat

#-------------------------- FUNCTIONS DEFINITION ------------------------------#

def is_dir(path):
    """
    Check if a given path is an existing directory.

    Args:
        path [string] = Path to the directory

    Returns:
        abs_path [string] = absolute path
        or quit
    """
    abs_path = os.path.abspath(path) # get absolute path

    # if not a directory
    if not os.path.isdir(abs_path):
        # check if it is a path to a file
        if os.path.isfile(abs_path):
            msg = "{0} is a file not a directory.".format(abs_path)
        # else the path doesn't not exist
        else:
            msg = "The path {0} does not exist.".format(abs_path)
        raise argparse.ArgumentTypeError(msg)

    return abs_path


def dir_not_exists(path):
    """
    Check if a path exist or not.

    Args:
        path [string] = Path

    Returns:
        abs_path [string] = absolute path if it doesn't exist
        or quit
    """
    abs_path = os.path.abspath(path)

    # if path exists
    if os.path.exists(abs_path):
        msg = ("The path {0} already exist. "
               "Please give another directory name".format(abs_path))
        raise argparse.ArgumentTypeError(msg)

    return abs_path


def is_fasta(path):
    """
    Check if a path is an existing fasta file, only checks the extension of the 
    file.

    Args:
        path [string] = Path to the file

    Returns:
        abs_path [string] = absolute path to the fasta file if it exists
        or quit
    """
    abs_path = os.path.abspath(path) # get absolute path

    # if not a file
    if not os.path.isfile(abs_path):
        # check if it is a path to a directory
        if os.path.isdir(abs_path):
            msg = "{0} is a directory not a file.".format(abs_path)
        # else the path doesn't not exist
        else:
            msg = "The path {0} does not exist.".format(abs_path)
        raise argparse.ArgumentTypeError(msg)

    # else, it's a file, check the extension
    else:
        split_filename = os.path.splitext(abs_path)
        ext = split_filename[1] # get the extension
        if not (ext == '.fa') or (ext == ".fasta"):
            msg = ("The given file '{0}' isn't a fasta file, "
                   "please provide a fasta file [.fa/.fasta]".format(abs_path))
            raise argparse.ArgumentTypeError(msg)

    return abs_path


def is_mode(text):
    """
    Check if the sequencing mode is 'PE' or 'SE', for reads.

    Args:
        text [string] = the text to check

    Returns:
        clean_text [string]
    """
    clean_text = text.upper()
    
    # if the text is not SE or PE
    if not (clean_text == 'SE' or clean_text == 'PE'):
        msg = "{0} isn't a valid mode ['PE' or 'SE' only].".format(clean_text)
        raise argparse.ArgumentTypeError(msg)

    return clean_text


def is_database(dbname, prog):
    """
    Check if the database is indexed with the mapping tool
    
    Args:
        dbname [string] = database name
        prog [string] = expected extension of the database of the mapping tool

    Returns :
        database [string] = for NovoAlign, the path to the file,
                            for Bowtie2 and BWA, the path to the database 
                                directory 
        or quit
    """

    db = os.path.abspath(dbname) # absolute path of the database

    if prog == 'novo':
        if not os.path.isfile(db):
            sys.exit("[ERROR] The database isn't indexed with NovoAlign")
        return db

    db_dir = os.path.dirname(db) # database directory

    # for bowtie2, check 6 files exists in the directory with the index 
    # extension .bt2
    if prog == 'bowtie2':
        ext = ['.bt2', '.bt2l']
        onlyfiles = [f for f in listdir(db_dir) 
                     if os.path.isfile(os.path.join(db_dir, f))
                     and (os.path.splitext(f)[1] in ext)]
        if not len(onlyfiles) == 6:
            sys.exit("[ERROR] The database isn't indexed with Bowtie2")
        return db

    # for bwa, check if files with the expected extension exists
    if prog == 'bwa':
        ext = ['.amb', '.ann', '.bwt', '.pac', '.sa']
        onlyfiles = [f for f in listdir(db_dir) 
                     if os.path.isfile(os.path.join(db_dir, f)) 
                     and (os.path.splitext(f)[1] in ext) ]
        if not len(onlyfiles) == 5:
            sys.exit("[ERROR] The database isn't indexed with BWA")
        return db


def create_index(filename, text, queue, index_name):
    """

    """
    # create a submission file for qrsh 
    with open(filename, "wt") as fileout:
        fileout.write(text)

    # make an executable file
    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)

    # launch the qrsh
    commandline = "qrsh -q {0} -cwd ./{1}".format(queue, filename)
    arg_split = shlex.split(commandline)
    index = os.path.splitext(index_name)[1]
    print "Variant calling : Creating {0} index".format(index[1:].upper())  
    try:
        p = subprocess.call(arg_split)
    except subprocess.CalledProcessError as e:
        p = e.p
        sys.exit(e.returncode)

    # wait until the index is created and then delete the file
    while not os.path.exists(index_name):
        time.sleep(1)
    os.remove(filename)

def find_fastq_files(file_list, mode):
    """
    Find fastq file by extension according to mode (Paired-end or Single end) 
    and rename them.
    
    Args:
        file_list [list] =  all files of a directory
        mode [string] = 'Single End' or 'Paire End'
    
    Returns:
        ext [str] = extension of FASTQ files
        num [int] = number of task to execute
        files_name [list] = list of all fastq filenames
    """

    ext_list = []
    filenames = []
    
    # Get a list of fastq files
    for file1 in file_list:
        split_filename = os.path.splitext(file1)
        ext_1 = split_filename[1]
        
        # check if compressed file
        if ext_1 == ".gz":
            ext = '.gz'
            split_filename = os.path.splitext(split_filename[0])
            ext_1 = split_filename[1]
        else:
            ext = ""
            
        # get only fastq files
        if (ext_1 == '.fq') or (ext_1 == '.fastq'):
            ext = ext_1 + ext
            if mode == 'SE':
                filenames.append(file1)
            # if mode PE
            else : 
                name_wo_ext = os.path.splitext(split_filename[0])[0]
                if (name_wo_ext[-1] == '1'):
                    mate_file = re.sub('1' + ext, '2' + ext, file1)
                    # check if mate is present
                    if mate_file in file_list:
                        filenames.append([file1, mate_file])
                    ext = "1" + ext
                    # get filename format
                    if (name_wo_ext[-2] == 'R') : 
                        ext = 'R' + ext
                    if (name_wo_ext[-2] == '_' or name_wo_ext[-3] == '_'):
                        ext = "_" + ext
                    ext_list.append(ext)

    # Get the number of task to execute
    num = len(filenames)
    if num == 0:
        sys.exit("[FATAL] No FASTQ file detected. FASTQ file names must have "
                 "the format: file_R1.fastq & file_R2.fastq. OR file_1.fastq "
                 "& file_2.fastq")

    # Get the extension of fastq files
    if mode == 'PE': 
        # check if all fastq files have the same extension
        if all(ext==ext_list[0] for ext in ext_list):
            ext = ext_list[0]
        else :
            sys.exit("[FATAL] All FASTQ files must have the same name format. "
                   "Example for Paired-end reads: "
                   "file_[R1/1].[fastq/fq] & file_[R2/2].[fastq/fq].")
    return ext, num, filenames


def create_dir(name, variant = False):
    """
    Function that create directories in the output directory: 
        - err, out, sam, bam, comptage for mapping mode
        - in addition: vcf and new_comptage for variant calling mode

    Args:
        name [string] = output directory name
        variant [True/False] = optinal argument, set to True for variant 
                               calling mode, [default : False]
    """
    try:
        os.mkdir(name)
        os.mkdir("{0}/out".format(name))
        os.mkdir("{0}/sam".format(name))
        os.mkdir("{0}/bam".format(name))
        os.mkdir("{0}/comptage".format(name))
        if variant: # if variant calling mode
            os.mkdir("{0}/vcf".format(name))
            os.mkdir("{0}/new_comptage".format(name))

    except OSError as ose:
        sys.exit("Cannot create {0} directory, "
                 "it already exists".format(ose.filename))


def write_tmp_file(file_list, output):
    """
    Write a file containing all the FASTQ file. This file will be read
    by the qsub submission script.

    Args:
        file_list [list] = list of fastq filenames
        output [string] = the output filename

    Returns:
        output [string] = output filename
    """
    output = "{0}/Files2read.txt".format(args['outdir']) # output name
    
    # write file
    with open(output, "wt") as out:
        for element in file_list:
            if len(element) == 2:
                out.write('\t'.join(element) + '\n')
            else :
                out.write(element + '\n')

    return output


def write_soum(param):
    """
    Write the qsub submission script.

    Args:
        param [dict] = containing all information needed for the submission 
                       script creation
    
    No returns
    """

    soumis = """#!/bin/sh

#$ -S /bin/bash
#$ -M {email}
#$ -m bea
#$ -q {queue}
#$ -N {jobname}
#$ -j y
#$ -o {stdout}
#$ -pe thread {threads} 
#$ -t 1-{num}

### MODULES
module add Python/2.7.8 {modules}

### INPUT FILES
{input}

### INPUT FILE BASENAME
BASE=`basename ${{INFILE_1%{ext}}}`

### OUTPUT DIRECTORY
OUTDIR={outdir}

### FUNCTIONS
function timer()
{{
    if [[ $# -eq 0 ]]; then
        echo $(date '+%s')
    else
        local  stime=$1
        etime=$(date '+%s')
        if [[ -z '$stime' ]]; then stime=$etime; fi
        dt=$((etime - stime))
        ds=$((dt % 60))
        dm=$(((dt / 60) % 60))
        dh=$((dt / 3600))
        printf '%d:%02d:%02d' $dh $dm $ds
    fi
}}

### PROGRAMS

echo $date
echo "Mapping files: $INFILE_1 & $INFILE_2" 
start_time=$(timer)
echo "Started at " $(date +"%T") 

start_time_{map_tool}=$(timer)
echo "Mapping with {map_tool} started at $(date +"%T")"
{map_cmd}
echo "Elapsed time with {map_tool} : $(timer $start_time_{map_tool})"

start_time_{count_tool}=$(timer)
echo "Mapping analysis with {count_tool} started at $(date +"%T")"
python {script_loc}/counting.py $OUTDIR/sam/${{BASE}}.sam \
$OUTDIR/comptage/${{BASE}}.txt --{count_tool} {bam}
echo "Elapsed time with {count_tool} : $(timer $start_time_{count_tool})"
{variant}
echo "Total duration :  $(timer $start_time)" """

    # Write the submission script
    with open("{0}/soumission.sh".format(args['outdir']), "wt") as out:
        out.write(soumis.format(**param))


def progress(count, total, suffix=''):
    """
    Function that prints a progress bar.

    Args:
        count [int] = number of executed events
        total [int] = total number of events
        suffix [str] = supplementary text to print
    """
    bar_len = 60
    filled_len = int(round(bar_len * count/float(total)))
    
    percents = round(100.0 * count / float(total),1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ..%s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()


#--------------------------------- MAIN ---------------------------------------#

if __name__ == '__main__' :
    
    ### ARGUMENT PARSER --------------------------------------------------------
    
    parser = argparse.ArgumentParser(description = "MBMA - Mapping Based "
                                                   "Microbiome Analysis")
    
    group = parser.add_argument_group('Options for commandline mode',
            description="For commandline mode :  (1)input, (2)database, \n"
                        "(3) output directory, (4)mapping tool and (5) read \n"
                        "counting method are obligatory arguments.\n"
                        "They can be supplied in any order.\n")

    group.add_argument("-o", "--outdir",
                       type = dir_not_exists,
                       metavar = "DIR", 
                       action = "store", 
                       help = "Program output directory")
    
    group.add_argument("-i", "--indir",
                       type = is_dir,
                       action = "store",
                       metavar = "DIR",
                       help = "Path to a directory containing all input FASTQ files")

    group.add_argument("-db","--ref_db",
                       type = str,
                       action = "store",
                       metavar = "STRING",
                       help = "Prefix of the reference indexed database.")

    group.add_argument("-fa","--ref_fasta",
                       type = is_fasta,
                       action = "store",
                       metavar = "FILE",
                       help = "The reference database in FASTA format.")    

    group.add_argument('-m', "--mode",
                       type = is_mode,
                       nargs = '?',
                       metavar = "PE/SE",
                       default = 'PE',
                       action="store",
                       help = "Mapping mode either paired-ends (PE) or single-ends (SE)"
                              " [default = 'PE']. \n")

    group.add_argument("-matrice", "--variant_matrice",
                       type = is_dir,
                       action = "store",
                       metavar = "DIR",
                       help = "Path to a directory containing all VCF of the variant matrice")

    group.add_argument("-t", "--threads",
                       type = int,
                       action = "store",
                       nargs = '?',
                       default = 1,
                       metavar = "INT",
                       help = "Number of processor to use. [default = 1]")

    group.add_argument("-e", "--email",
                       type = str,
                       metavar="STRING",
                       help = "Email for qsub notification.\n")

    group.add_argument("-q", "--queue",
                       type = str,
                       metavar = "STRING",
                       help = "Queue name for qsub.\n")
    
    group.add_argument("-j", "--jobname",
                       type = str,
                       nargs = '?',
                       default = "Job",
                       metavar = "STRING",
                       help = "Job name for qub.\n")

    group.add_argument("-s", "--strict",
                       action = 'store_const',
                       const = 'strict',
                       metavar = "STRING",
                       help = "Strict mapping.\n")

    mapping_tool = parser.add_mutually_exclusive_group(required=False)
    
    mapping_tool.add_argument('--bowtie2', 
                              action = 'store_const',
                              const = 'True',
                              help = "Use Bowtie2 to map read against reference"
                                     " database\n")
    
    mapping_tool.add_argument('--bwa', 
                              action='store_const',
                              const = 'True',
                              help = "Use BWA to map read against reference "
                                     "database\n")

    mapping_tool.add_argument('--novo', 
                              action='store_const',
                              const = 'True',
                              help = "Use NovoAlign to map read against reference "
                                     "database\n")

    count_mode = parser.add_mutually_exclusive_group(required=False)
    
    count_mode.add_argument('--best', 
                            action = 'store_const',
                            const = 'True',
                            help = "Use the mode 'Best' to count mapped read\n")
    
    count_mode.add_argument('--ex_aequo', 
                              action='store_const',
                              const = 'True',
                              help = "Use the mode 'Ex-aequo' to count mapped read\n")
    
    count_mode.add_argument('--shared', 
                              action='store_const',
                              const = 'True',
                              help = "Use the mode 'Shared' to count mapped read\n")
    
    work_mode = parser.add_mutually_exclusive_group(required=False)
    
    work_mode.add_argument('--species', 
                            action = 'store_const',
                            const = 'True',
                            help = "Prediction of species using RefMG.v1 database\n")
    
    work_mode.add_argument('--resistance', 
                              action='store_const',
                              const = 'True',
                              help = "Prediction of resistance genes using ResFinder database\n")
    
    
    ## PRINT HELP --------------------------------------------------------------

    if not len(sys.argv) >= 2 :
        parser.print_help()
        exit(1)

    # locate script dir
    script_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    ## PARSING COMMANDLINE -----------------------------------------------------

    # Parse commandline arguments
    try :
        args = parser.parse_args()
        args = vars(args)
    except:
        exit(1)

    # check the arguments
        # input and output 
    if not args['outdir']:
        parser.error("output directory is not supplied, you must specify an "
                     "output directory by -o/--outdir.")

    if not args['indir']:
        parser.error("input directory is not supplied, you must specify a "
                     "directory containing all input files by -i/--indir.")

        # SGE Cluster
    if not args['email']:
        parser.error("email id is not supplied, you must specify an email id "
                     "by -e/--email.")

    if not args['queue']:
        parser.error("queue name is not supplied, you must specify a queue "
                     "name by -q/--queue.")
    
    if args['threads'] < 1:
        sys.stderr.write("[Warning] Illegal number of threads provided: %i, "
                          "MBMA will use a single thread by default" 
                          % args['threads'])
        args['threads'] = 1

        # Variant calling
    if args['variant_matrice']:
        if not args['ref_fasta']:
            parser.error("the database fasta file is not supplied for variant "
                         "calling mode, you must specify a fasta file by "
                         "-fa/--ref_fasta.")

    if args['ref_fasta']:
        if not args['variant_matrice']:
            parser.error("directory of the database variant matrices is not "
                         "supplied for the variant calling mode, you must "
                         "specify a directory by -matrice/--variant_matrice")

        # Working modes : species and resistance
    if not (args['species'] or args['resistance']):
        # database, mapping tool and counting method should be provided
    	if not args['ref_db']:
        	parser.error("reference database is not supplied, you must specify"
                         " a reference database by -db/--ref_db.")

        if not args['bowtie2'] or args['novo'] or args['bwa']:
        	parser.error("one of the arguments --bowtie2 --bwa --novo is "
                         "required")

        if not args['best'] or args['ex_aequo'] or args['novo']:
        	parser.error("one of the arguments --best --ex_aequo --shared is "
                         "required")

        # working modes parameters
    if 'species' in args:
        args.update({'bowtie2':'True',
                     'shared':'True',
                     'strict':'strict',
                     'ref_db':script_path + '/databases/index/refmg_bowtie2/' + 
                              'refmg'})

    if 'resistance' in args:
        args.update({'bowtie2':'True',
                     'shared':'True',
                     'strict':'strict',
                     'ref_db':script_path + '/databases/index/' + 
                              'clustered_ResFinder_bowtie2/resfinder98',
                     'ref_fasta':script_path + '/databases/' + 
                                 'clustered_ResFinder.fa',
                     'variant_matrice':script_path + '/matrices/' + 
                                       'clustered_ResFinder/'})

        # cleaning the dictionnary
    for key, value in args.items():
        if value == None:
            del(args[key])

    # check database's index
        
        # mapping tool
    if 'bowtie2' in args:
        args['ref_db'] = is_database(args['ref_db'], 'bowtie2')
    elif 'bwa' in args:
        args['ref_db'] = is_database(args['ref_db'], 'bwa')
    elif 'novo' in args:
        args['ref_db'] = is_database(args['ref_db'], 'novo')
        
        # variant calling
    if args['ref_fasta']:
        fasta = args['ref_fasta']
        fasta_dict = os.path.splitext(fasta)[0] + ".dict"
        fasta_fai = fasta + '.fai'
        # picard index checking
        if not os.path.isfile(fasta_dict):
            filename = 'dict_index.sh'
            text = ("source /local/gensoft2/adm/etc/profile.d/modules.sh\n"
                    "module add picard-tools/1.94\n"
                    "CreateSequenceDictionary R= {0} O= {1}\n".format(fasta, 
                                                                    fasta_dict))
            create_index(filename, text, args['queue'],fasta_dict)

        # samtools index checking
        if not os.path.isfile(fasta_fai):
            filename = 'fai_index.sh'
            text = ("source /local/gensoft2/adm/etc/profile.d/modules.sh\n"
                    "module add samtools/1.2\n"
                    "samtools faidx {0}\n".format(fasta))
            create_index(filename, text, args['queue'],fasta_fai)


    ### INPUT ------------------------------------------------------------------
    
    files = [] # files to process
    
    # get absolute path of all files in input directory
    files = os.listdir(args['indir'])
    files = [ '{0}/{1}'.format(args['indir'],file1) for file1 in files]
    
    # number of tasks
    args['ext'], args['num'], files_name = find_fastq_files(files, args['mode'])


    ### OUTPUT -----------------------------------------------------------------

    # create output directories
    if 'ref_fasta' in args:
        create_dir(args['outdir'], variant=True)
    else:
        create_dir(args['outdir'])
    
    # create a temporary file
    args['read_file'] = write_tmp_file(files_name, args['outdir'])

    
    # WRITE QSUB SOUMISSION SCRIPT ---------------------------------------------

    # input files
    if (args['mode'] == 'PE'):
        args['input'] = ('INFILE_1=`sed "${{SGE_TASK_ID}}q;d" {read_file} |'
                         ' cut -f1`\n'
                         'INFILE_2=`sed "${{SGE_TASK_ID}}q;d" {read_file} | '
                         'cut -f2`'.format(**args))
    else :
        args['input'] = ('INFILE_1=`sed "${{SGE_TASK_ID}}q;d" '
                         '{read_file}`'.format(**args))

    # output directory
    args['stdout'] = '{0}/out'.format(args['outdir'])

    # mapping tools    
        # Bowtie2
    if 'bowtie2' in args :
        args['modules'] = "bowtie2/2.2.6 "
        args['map_tool'] = args['bowtie2']
        
        # commandline for bowtie2
        cmd = ("bowtie2 -p {threads} -x {ref_db} -q --local "
               "--sensitive-local ".format(**args))

        # input
        if args['mode'] == 'PE':
            cmd += "-1 $INFILE_1 -2 $INFILE_2 "
        else :
            cmd += "-U ${INFILE_1} "
        
        # mapping strict
        if 'strict' in args:
            cmd += "--score-min G,40,8 "

        # get all alignements
        if 'ex_aequo' in args or 'shared' in args :
            cmd += "-a "

        # output
        cmd += "-S $OUTDIR/sam/${BASE}.sam "
        
        # get cmd 
        args['map_cmd'] = cmd
    
        ### BWA
    elif 'bwa' in args :
        args['modules'] = "bwa/0.7.7 "
        args['map_tool'] = args['bwa']
        
        # commandline for bwa
        cmd = "bwa mem -t {threads} {ref_db} ".format(**args)
        
        # input
        if args['mode'] == 'PE':
            cmd += "$INFILE_1 $INFILE_2 "
        else :
            cmd += "$INFILE_1 "

        # mapping strict
        if 'strict' in args:
            cmd += "-T 60 "

        # get all alignements
        if 'ex_aequo' in args or 'shared' in args :
            cmd += "-a "

        # output
        cmd +=  "> $OUTDIR/sam/${BASE}.sam "

        # get cmd
        args['map_cmd'] = cmd
    
        # Novoalign
    elif 'novo' in args :
        args['modules'] = "novocraft/V3.02.12 "
        args['map_tool'] = args['novo']
        
        # commandline for novo
        cmd = "novoalign -d {ref_db} -F STDFQ -o SAM ".format(**args)
        
        # input
        if args['mode'] == 'PE':
            cmd += "-f $INFILE_1 $INFILE_2  "

        # get all alignements
        if 'ex_aequo' in args or 'shared' in args :
            cmd += "-r All "
        else :
            cmd += '-r Random '

        # output
        cmd +=  "> $OUTDIR/sam/original_${BASE}.sam \n"

        # clean sam file, by removing bad alignements (score = 0)
        cmd += ("grep -v 'AS:i:0' $OUTDIR/sam/original_${BASE}.sam "
                "> $OUTDIR/sam/${BASE}.sam ")
        
        # get cmd
        args['map_cmd'] = cmd
    
    # mapping tools
    args['script_loc'] = script_path
    if 'best' in args:
        args['count_tool'] = 'best'
    elif 'ex_aequo' in args:
        args['count_tool'] = 'ex_aequo'
    elif 'shared' in args:
        args['count_tool'] = 'shared'
    if 'ref_fasta' in args:
        args['bam'] = '-bam'
    else :
        args['bam'] = ''
   
    # variant calling
    args['variant']= ""
    if 'ref_fasta' in args:
        args['modules'] += ("samtools/1.2 GenomeAnalysisTK/3.4-0 "
                            "picard-tools/1.94 ")
        args['variant'] = ("""
start_time_variant=$(timer)
echo "Variant calling analysis with GATK started at $(date +"%T")"
java -jar  \
/local/gensoft2/exe/picard-tools/1.78/libexec/AddOrReplaceReadGroups.jar \
I=$OUTDIR/bam/filtered_${{BASE}}.bam O=$OUTDIR/bam/grp_${{BASE}}.bam RGID=4 \
RGLB=lib1 RGPL=illumina RGPU=unit1 RGSM=20

samtools index $OUTDIR/bam/grp_${{BASE}}.bam

GenomeAnalysisTK -T SplitNCigarReads -R {ref_fasta} \
-I $OUTDIR/bam/grp_${{BASE}}.bam -o $OUTDIR/bam/bon_${{BASE}}.bam \
-rf ReassignOneMappingQuality -RMQF 255 -RMQT 60 -U ALLOW_N_CIGAR_READS

GenomeAnalysisTK -T HaplotypeCaller -R {ref_fasta} \
-I $OUTDIR/bam/bon_${{BASE}}.bam --genotyping_mode DISCOVERY \
-stand_call_conf 0 -stand_emit_conf 0 -o $OUTDIR/vcf/${{BASE}}.vcf

python {script_loc}/variant_predict.py {variant_matrice} \
$OUTDIR/vcf/${{BASE}}.vcf $OUTDIR/comptage/${{BASE}}.txt \
$OUTDIR/new_comptage/${{BASE}}.txt
echo "Elapsed time with GATK : $(timer $start_time_variant)
""".format(**args))


    # LAUNCH QSUB SOUMISSION SCRIPT --------------------------------------------

    try :
        write_soum(args)
    except (IOError, OSError) :
        shutil.rmtree(args['outdir'])
        sys.exit("Error : Writing submission script")
    except :
        shutil.rmtree(args['outdir'])
        sys.exit("Unexpected error: {0}".format(sys.exc_info()[0]))

    commandline = "qsub {outdir}/soumission.sh".format(**args)
    arg_split = shlex.split(commandline)
    
    with open("{0}/stdout.txt".format(args['outdir']),"at") as out, \
         open("{0}/stderr.txt".format(args['outdir']),"at") as err:
        try:
            p = subprocess.call(arg_split, stdout=out, stderr=err)

        except subprocess.CalledProcessError as e:
            p = e.p
            sys.exit(e.returncode)

    errfile = "{outdir}/stderr.txt".format(**args)
    if os.stat(errfile).st_size != 0:
        with open(errfile, "at") as errfile:
            sys.stderr.write(errfile.read())
        
        shutil.rmtree(args['outdir'], ignore_errors=True)
        sys.exit(1)
    
    
    # CHECK PROGRESSION --------------------------------------------------------
    
    nb_tables = 0
        
    while (nb_tables < args['num']):
        time.sleep(2)
        # directory of the counting tables
        count_table_dir = 'comptage'
        if 'ref_fasta' in args:
            count_table_dir = 'new_comptage'
        # getnb of created files in the directory 
        nb_tables = len(glob.glob('{0}/{1}/*.txt'.format(args['outdir'], 
                                                         count_table_dir)))
        # print progression
        progress(nb_tables, args['num'], 
                '{0} count table out of {num} created'.format(nb_tables,**args))


    # COUNT MATRIX CREATION ----------------------------------------------------
    
    if (nb_tables == args['num']):
        
        # delete temporary file
        os.remove(args['read_file'])

        # delete old count table directory and rename the new as "comptage" :
        old_dir = args['outdir'] + '/comptage'
        new_dir = args['outdir'] + '/new_comptage'
        shutil.rmtree(old_dir)
        os.rename(new_dir, old_dir)

        # count matrix creation
        with open("{0}/stdout.txt".format(args['outdir']),"at") as out, \
             open("{0}/stderr.txt".format(args['outdir']),"at") as err:
            try :
                commandline = ("python {0}/count_matrix.py -d {1} "
                               "-o {1}/count_matrix.txt".format(script_path,
                                                                old_dir))
            
                args = shlex.split(commandline)
                p = subprocess.call(args,stdout=out, stderr=err)
            
            except subprocess.CalledProcessError as e:
                p = e.p
                sys.exit(e.returncode)

    sys.exit("MBMA successfully completed")