#!/usr/bin/python
#GenomePy: a functional and simple library for genomic analysis

import copy
import StringIO


def tab2fasta(tab_file):
    tabs = ensure_file(tab_file)
    newlines = []
    for line in tabs:
        fields = line.replace('\n','').replace('\r','').split('\t')
        newlines.append('>'+fields[0]+'\n'+fields[1])
    return "\n".join(newlines)


def fasta2tab(fasta_file):
    fasta = ensure_file(fasta_file)
    newlines = []
    for line in fasta:
        if line[0] == '>':
            newlines.append(line[1:].replace('\n','').replace('\r','') + '\t')
        else:
            newlines[-1] = newlines[-1] + line.replace('\n','').replace('\r','')
    return '\n'.join(newlines)
    



def ensure_file(potential_file):
    """takes an input that can be either a file location, opened file, or string, and returns an opened file or file like object.
    Used to make downstream applications robust to different input types"""
    if type(potential_file).__name__ == "file":
        return potential_file
    else:
        try:
            return open(potential_file)
        except IOError:
            return StringIO.StringIO(potential_file)


def read_to_string(potential_file):
    """Tries to read "potential_file" into string- first as file location,
    then file, then string."""
    try:
        output_string = open(potential_file).read().replace('\r','')
    except IOError:
        try:
            output_string = potential_file.read().replace('\r','')
        except AttributeError:
            output_string = potential_file.replace('\r','')
    return output_string


def apollo2genome(apollo_gff):
    apollo_list = read_to_string(apollo_gff).split('>')
    gff3 = apollo_list[0]
    fasta = '>' + apollo_list[1]
    return Genome(fasta,gff3,annotation_format='gff3')



def starjunc2gff(starjunc, output = 'string'):
    """parses junction file from STAR RNAseq aligner and returns an apollo-style gff3. Output can be "string", "list", or "print"."""
    if output != 'print':
        outlines = []
    junc_file = ensure_file(starjunc)
    strands = ['.','+','-']
    counter = 1
    for line in junc_file:
        ID = "StarAlignment_" + str(counter)
        counter = counter + 1
        atts = line.split('\t')
        stop1 = int(atts[1]) - 1
        start1 = stop1 - 20
        start2 = int(atts[2]) + 1
        stop2 = start2 + 20
        gffline1 = '\t'.join([atts[0],'star','match',str(start1),str(stop2),atts[6], strands[int(atts[3])],'.','ID=' + ID])
        gffline2 = '\t'.join([atts[0],'star','match_part',str(start1),str(stop1),atts[6], strands[int(atts[3])],'.','ID=' + ID + '-part1;Parent=' + ID])
        gffline3 = '\t'.join([atts[0],'star','match_part',str(start2),str(stop2),atts[6], strands[int(atts[3])],'.','ID=' + ID + '-part2;Parent=' + ID])
        if output == 'print':
            print gffline1
            print gffline2
            print gffline3
        else:
            outlines.append(gffline1)
            outlines.append(gffline2)
            outlines.append(gffline3)
    if output == "string":
        return "\n".join(outlines)
    elif output == "list":
        return outlines
    elif output == "print":
        pass
    else:
        print "invalid output format"


def vulgar2gff(vulgarlist, feature_types=['match','match_part'],source='exonerate'):
    """takes vulgar alignment list (e.g. vulgarstring.split() ) and outputs gff lines. For eventual use with a read_exonerate function"""
    #sets variables to be added to gff lines
    qname = vulgarlist[0] + '-against-' + vulgarlist[4]
    qstart = vulgarlist[1]
    qend = vulgarlist[2]
    qstrand = vulgarlist[3]
    tname = vulgarlist[4]
    tstart = vulgarlist[5]
    tend = vulgarlist[6]
    tstrand = vulgarlist[7]
    score = vulgarlist[8]
    vulgartrips = vulgarlist[9:]
    addfeat = False
    IDnum = 1
    if tstrand == "+":
        tposition = int(tstart) + 1
    else:
        tposition = int(tstart)
        tend = str(int(tend)+1)
    #makes top level gff line for hit
    gfflines = ["\t".join([tname,source,feature_types[0],str(tposition),tend,score,tstrand,'.','ID='+qname])]
    #iterates over matches within hit to make bottom level feature gff lines
    for i in range(len(vulgartrips)):
        field = vulgartrips[i]
        if i % 3 == 0:
            if field == 'M' or field == 'S' or field == 'G' or field == 'F':
                if not addfeat:
                    addfeat = True
                    line_to_add = [tname,source,feature_types[1]]
                    coords = [str(tposition)]
                else:
                    pass
            elif addfeat:
                gfflines.append('\t'.join(line_to_add+[str(min(coords)),str(max(coords)),'.',tstrand,'.',
                                                       'ID='+qname+'_'+feature_types[1]+str(IDnum)+';Parent='+qname]))
                IDnum = IDnum + 1
                addfeat = False
            else:
                pass
        if i % 3 == 2:
            if tstrand == "+":
                tposition = tposition + int(field)
            elif tstrand == "-":
                tposition = tposition - int(field)
            if addfeat == True:
                if tstrand == '+':
                    coords.append(str(tposition-1))
                elif tstrand == '-':
                    coords.append(str(tposition+1))
    if addfeat:
        gfflines.append('\t'.join(line_to_add+[str(min(coords)),str(max(coords)),'.',tstrand,'.',
                                                       'ID='+qname+'_'+feature_types[1]+str(IDnum)+';Parent='+qname]))
    return '\n'.join(gfflines)


def read_exonerate(exonerate_output,annotation_set_to_modify = None):
    if annotation_set_to_modify == None:
        annotation_set = AnnotationSet()
    else:
        annotation_set = annotation_set_to_modify
    exonerate_lines = read_to_string(exonerate_output).split('\n')
    gfflines = []
    IDdic = {}
    qname = ""
    tname = ""
    for line in exonerate_lines:
        if line[:16] == "         Query: ":
            qname = line[16:]
        elif line[:16] == "        Target: ":
            tname = line[16:].replace(':[revcomp]','').replace('[revcomp]','')
            if tname[-1] == " ":
                tname = tname[:-1]
        elif line[:8] == "vulgar: ":
            vulgar_line_list = line[8:].split()
            #trying to makesure IDs are unique
            vulgar_line_list[0] = qname
            vulgar_line_list[4] = tname
            ID = vulgar_line_list[0] + '-against-' + vulgar_line_list[4]
            if ID in IDdic:
                vulgar_line_list[0] = vulgar_line_list[0] + str(IDdic[ID])
                IDdic[ID] = IDdic[ID] + 1
            else:
                IDdic[ID] = 1
            gfflines.append(vulgar2gff(vulgar_line_list))
    read_gff3("\n".join(gfflines), annotation_set_to_modify = annotation_set)
    if annotation_set_to_modify == None:
        return annotation_set
    
    
def write_longform_gff(annotation_set,keep_UTR_features = False):
    """returns gff string formated for compatability with Apollo genome annotation """
    gfflines = []
    fields = ['seqid','source','feature_type','get_coords()[0]','get_coords()[1]','score','strand','phase']
    #adds matches to gff
    if 'match' in annotation_set.__dict__:
        for match in annotation_set.match:
            match_obj = annotation_set.match[match]
            newline_list = []
            for field in fields:
                try:
                    newline_list.append(str(eval('match_obj.' + field)))
                except:
                    newline_list.append('.')
            attribute_list = ['ID=' + match_obj.ID]
            for attribute in match_obj.__dict__:
                if not attribute in fields+['annotation_set','parent','child_list','ID']:
                    attribute_list.append(attribute + '=' + eval('match_obj.' + attribute))
            newline_list.append(';'.join(attribute_list))
            gfflines.append('\t'.join(newline_list))
            for match_part in match_obj.child_list:
                match_part_obj = annotation_set[match_part]
                newline_list = []
                for field in fields:
                    try:
                        newline_list.append(str(eval('match_part_obj.' + field)))
                    except:
                        newline_list.append('.')
                attribute_list = ['ID=' + match_part_obj.ID,'Parent=' + match_part_obj.parent]
                for attribute in match_part_obj.__dict__:
                    if not attribute in fields+['annotation_set','parent','child_list','ID','coords']:
                        attribute_list.append(attribute + '=' + eval('match_part_obj.' + attribute))
                newline_list.append(';'.join(attribute_list))
                gfflines.append('\t'.join(newline_list))
        #adds genes to gff
    if 'gene' in annotation_set.__dict__:
        for gene in annotation_set.gene:
            gene_obj = annotation_set.gene[gene]
            newline_list = []
            for field in fields:
                try:
                    newline_list.append(str(eval('gene_obj.' + field)))
                except:
                    newline_list.append('.')
            attribute_list = ['ID='+gene_obj.ID]
            for attribute in gene_obj.__dict__:
                if not attribute in fields+['annotation_set','parent','child_list','ID']:
                    attribute_list.append(attribute + '=' + eval('gene_obj.' + attribute))
            newline_list.append(';'.join(attribute_list))
            gfflines.append('\t'.join(newline_list))
            for gene_child in gene_obj.child_list:
                gene_child_obj = annotation_set[gene_child]
                if gene_child_obj.feature_type == 'transcript':
                    transcript_obj = gene_child_obj
                    newline_list = []
                    for field in fields:
                        try:
                            newline_list.append(str(eval('transcript_obj.'+field)).replace('transcript','mRNA'))
                        except:
                            newline_list.append('.')
                    attribute_list = ['ID='+transcript_obj.ID,'Parent='+transcript_obj.parent]
                    for attribute in gene_obj.__dict__:
                        if not attribute in fields+['annotation_set','parent','child_list','ID']:
                            attribute_list.append(attribute + '=' + eval('transcript_obj.' + attribute))
                    newline_list.append(';'.join(attribute_list))
                    gfflines.append('\t'.join(newline_list))
                    exondict = {}
                    CDS_UTR_dict = {}
                    for transcript_child in transcript_obj.child_list:
                        transcript_child_obj = annotation_set[transcript_child]
                        line_base_list = []
                        for field in fields:
                            try:
                                line_base_list.append(str(eval('transcript_child_obj.'+ field)))
                            except:
                                line_base_list.append('.')
                        exon_attributes = 'ID=' + transcript_child_obj.ID + '-exon;Parent=' + transcript_child_obj.parent
                        transcript_child_attribute_list = ['ID=' + transcript_child_obj.ID, 'Parent=' + transcript_child_obj.parent]
                        for attribute in transcript_child_obj.__dict__:
                            if not attribute in fields+['annotation_set','parent','child_list','ID','coords']:
                                transcript_child_attribute_list.append(attribute + '=' + eval('transcript_child_obj.' + attribute))
                        transcript_child_attributes = ';'.join(transcript_child_attribute_list)
                        exondict[transcript_child_obj.coords] = '\t'.join(line_base_list).replace('CDS','exon').replace('UTR','exon') + '\t' + exon_attributes
                        CDS_UTR_dict[transcript_child_obj.coords] = '\t'.join(line_base_list) +'\t' + transcript_child_attributes
                    exondict_list = list(exondict)
                    exondict_list.sort()
                    CDS_UTR_dict_list = list(CDS_UTR_dict)
                    CDS_UTR_dict_list.sort()
                    #merges adjacent exons from abbutting UTRs and CDSs and writes exon gff lines
                    for i in range(len(exondict_list) - 1):
                        if exondict_list[i][1] + 1 == exondict_list[i+1][0]:
                            del exondict[exondict_list[i]]
                            new_exon_list = exondict[exondict_list[i+1]].split('\t')
                            exondict[exondict_list[i+1]] = '\t'.join(new_exon_list[:3]+[str(exondict_list[i][0]),str(exondict_list[i+1][1])]+new_exon_list[5:])
                        else:
                            gfflines.append(exondict[exondict_list[i]])
                    gfflines.append(exondict[exondict_list[-1]])
                    for i in CDS_UTR_dict_list:
                        if CDS_UTR_dict[i].split('\t')[2] == 'CDS' or keep_UTR_features:
                            gfflines.append(CDS_UTR_dict[i])
                else:
                    print 'ERROR: currently only accepts AnnotationSets with gene format CDS/UTR -> transcript -> gene'
                    break
    return '\n'.join(gfflines)


def read_gff3(gff3,annotation_set_to_modify = None,gene_hierarchy = ['gene','mRNA',['CDS','five_prime_UTR','three_prime_UTR']],
              other_hierarchies = [['match','match_part']],features_to_ignore = ['exon'],
              features_to_replace = [('protein_match','match'),('expressed_sequence_match','match')]):
    #reads gff3 to string if supplied as a file or file location
    gff_file = ensure_file(gff3)
    #reformates features_to_replace to be used in later command
    for feature in features_to_replace[:]:
        features_to_replace.append(str(feature))
        features_to_replace.remove(feature)
    #checks if annotation_set is given and creates annotation_set if not
    if annotation_set_to_modify == None:
        annotation_set = AnnotationSet()
    else:
        annotation_set = annotation_set_to_modify
    #this dictionary helps generate names if features are passed with parents but not IDs
    generate_ID_from_parent_dict = {}
    #this dictionary helps generate names if features passed with identical ID fields
    generate_new_ID_dict = {}
    #Fills annotiation_set
    for gff_line_with_return in gff_file:
        gff_line = gff_line_with_return.replace('\n','').replace('\r','')
        if len(gff_line) > 1:
            if gff_line[0] != '#' and gff_line.count('\t') == 8:
                try:
                    del parent
                except:
                    pass
                try:
                    del ID
                except:
                    pass
                gff_fields = gff_line.split('\t')
                other_attributes = {}
                seqid = gff_fields[0]
                other_attributes['source'] = gff_fields[1]
                feature_type = eval('gff_fields[2].replace' + '.replace'.join(features_to_replace))
                other_attributes['score'] = gff_fields[5]
                other_attributes['strand'] = gff_fields[6]
                for additional_attribute in gff_fields[8].split(';'):
                    if '=' in additional_attribute:
                        attr_split = additional_attribute.split('=')
                        if attr_split[0] == 'ID':
                            ID = attr_split[1]
                        elif attr_split[0] == 'Parent':
                            parent = attr_split[1]
                        else:
                            other_attributes[attr_split[0]] = attr_split[1]
                #checks for ID and/or parent in attribute field
                try:
                    ID
                except NameError:
                    try:
                        ID_base = parent + '-' + feature_type
                        if not ID_base in generate_ID_from_parent_dict:
                            generate_ID_from_parent_dict[ID_base] = 0
                        ID = parent + '-' + feature_type + str(generate_ID_from_parent_dict[ID_base])
                        generate_ID_from_parent_dict[ID_base] = generate_ID_from_parent_dict[ID_base] + 1
                    except NameError:
                        print "This gff (or at least one feature therein) seems to have an attributes field without\
                        'ID' or 'Parent' varaibles. This is not yet supported."
                        return
                #checks if feature with same ID already exists, generates a new ID if so. This should only happen with
                #base level features in dumb gff3s, otherwise something is wrong.
                try:
                    annotation_set[ID]
                    if ID in generate_new_ID_dict:
                        generate_new_ID_dict[ID] = generate_new_ID_dict[ID] + 1
                    else:
                        generate_new_ID_dict[ID] = 1
                    ID = ID + '_' + str(generate_new_ID_dict[ID])
                except:
                    pass
                #checks if feature_type in annotation_set, adds if not unless in features_to_ignore
                if not feature_type in annotation_set.__dict__ and not feature_type in features_to_ignore:
                    setattr(annotation_set, feature_type, {})
                #sets parent to None if does not exist
                try:
                    parent
                except NameError:
                    parent = None
                #creates annotations
                if feature_type in gene_hierarchy[-1] :
                    coords_list = [int(gff_fields[3]),int(gff_fields[4])]
                    coords_list.sort()
                    coords=tuple(coords_list)
                    if feature_type == 'CDS':
                        renamed_feature_type = 'CDS'
                    else:
                        renamed_feature_type = 'UTR'
                    eval('annotation_set.' + renamed_feature_type)[ID] = BaseAnnotation(ID,seqid,coords,renamed_feature_type,parent,
                                                                              other_attributes = copy.copy(other_attributes),
                                                                              annotation_set = annotation_set)
                elif feature_type in gene_hierarchy:
                    make_feature = True
                    renamed_feature_type = feature_type
                    if len(gene_hierarchy) > 2:
                        if feature_type == gene_hierarchy[1]:
                            renamed_feature_type = 'transcript'
                    if make_feature:
                        eval('annotation_set.' + renamed_feature_type)[ID] = ParentAnnotation(ID, seqid, renamed_feature_type,parent = parent,
                                                                                  annotation_set = annotation_set, other_attributes = copy.copy(other_attributes))
                elif feature_type in features_to_ignore:
                    pass
                else:
                    in_hierarchy = False
                    for other_hierarchy in other_hierarchies:
                        if feature_type == other_hierarchy[-1]:
                            in_hierarchy = True
                            coords_list = [int(gff_fields[3]),int(gff_fields[4])]
                            coords_list.sort()
                            coords=tuple(coords_list)
                            create_parents_chain = other_hierarchy[:-1]
                            create_parents_chain.reverse()
                            eval('annotation_set.' + feature_type)[ID] = BaseAnnotation(ID, seqid, coords, feature_type, parent,
                                                                              other_attributes = copy.copy(other_attributes),
                                                                              annotation_set = annotation_set,
                                                                              create_parents_chain = create_parents_chain)
                        elif feature_type in other_hierarchy:
                            in_hierarchy = True
                            eval('annotation_set.' + feature_type)[ID] = ParentAnnotation(ID, seqid, feature_type, parent = parent,
                                                                                          annotation_set = annotation_set, other_attributes = copy.copy(other_attributes))
                    if not in_hierarchy:
                        coords_list = [int(gff_fields[3]),int(gff_fields[4])]
                        coords_list.sort()
                        coords=tuple(coords_list)
                        eval('annotation_set.' + feature_type)[ID] = BaseAnnotation(ID, seqid, coords, feature_type, parent,
                                                                              other_attributes = copy.copy(other_attributes),
                                                                              annotation_set = annotation_set,
                                                                              create_parents_chain = None)
    if annotation_set_to_modify == None:
        return(annotation_set)


def read_gtf(gtf,annotation_set_to_modify = None, parent_attribute = None, ID_attribute = None):
    gtf_file = ensure_file(gtf)
    if annotation_set_to_modify == None:
        annotation_set = AnnotationSet()
    else:
        annotation_set = annotation_set_to_modify
    for line in gtf_file:
        fields = line.split('\t')
        seqid = fields[0]
        source = fields[1]
        feature = fields[2]
        coords = [int(fields[3]),int(fields[4])]
        coords.sort()
        score = fields[5]
        strand = fields[6]
        attributes = fields[8].split(';')
        attribute_dic = {}
        for attribute in attributes:
            try:
                attribute_dic[attribute.split()[0]] = attribute.split()[1]
            except:
                if unnamed_attributes in attribute_dic:
                    attribute_dic[unnamed_attributes].append(attribute)
                else:
                    attribute_dic[unnamed_attributes] = [attribute]
        if ID_attribute != None:
            ID = attribute_dic[ID_attribute]
        elif parent_attribute != None:
            ID = attribute_dic[parent_attribute] + "-" + feature + "-" + str(coords[0])
        else:
            ID = seqid + '-' + feature + '-' + str(coords[0])
        if parent_attribute != None:
            parent = attribute_dic[parent_attribute]
        else:
            parent = None
        
    


def read_cegma_gff(cegma_gff,annotation_set_to_modify = None):
    """reads gff produced by CEGMA and returns AnnotationSet populated by CEGMA predictions"""
    modified_gff = read_to_string(cegma_gff).replace('\tFirst\t','\tCDS\t').replace('\tInternal\t','\tCDS\t').replace('\tTerminal\t','\tCDS\t').replace('KOG','Parent=KOG')
    annotation_set = read_gff3(modified_gff,annotation_set_to_modify = annotation_set_to_modify, gene_hierarchy=['CDS'])
    if annotation_set_to_modify == None:
        return annotation_set


def read_blast_csv(blast_csv,annotation_set_to_modify = None,hierarchy = ['match','match_part'], source = 'blast', find_truncated_locname = False):
    """Reads csv output from blast (-outfmt 10) into an AnnotationSet object. Currently does not string hits together because I'm
    biased towards working on genes in tandem arrays where stringing hits together is annoying. May add option in future."""
    #reads blast_csv from file location, file, or string
    blast_lines = read_to_string(blast_csv).split('\n')
    #checks if annotation_set is given and creates annotation_set if not
    if annotation_set_to_modify == None:
        annotation_set = AnnotationSet()
    else:
        annotation_set = annotation_set_to_modify
    id_generator_dict = {}
    feature_type = hierarchy[-1]
    create_parents_chain = hierarchy[:-1]
    create_parents_chain.reverse()
    if not feature_type in annotation_set.__dict__:
        setattr(annotation_set, feature_type, {})
    if find_truncated_locname:
        if annotation_set.genome == None:
            print '"warning: find_truncated_locname" was set to true, but annotation set has no associated genome object so this cannot be done'
            find_truncated_locname = False
        else:
            genome_seqids = annotation_set.genome.get_seqids()
    for line in blast_lines:
        fields = line.split(',')
        if len(fields) > 8:
            seqid = fields[1]
            if find_truncated_locname:
                if not seqid in genome_seqids:
                    for genome_seqid in genome_seqids:
                        if seqid == genome_seqid.split()[0]:
                            seqid = genome_seqid
                            break
            tstart = int(fields[8])
            tend = int(fields[9])
            if tstart < tend:
                coords = (tstart,tend)
                strand = '+'
            else:
                coords = (tend,tstart)
                strand = '-'
            score = fields[11]
            IDbase = fields[0]
            if IDbase in eval('annotation_set.' + feature_type):
                ID = IDbase + '-' + str(id_generator_dict[IDbase])
                id_generator_dict[IDbase] = id_generator_dict[IDbase] + 1
                while ID in eval('annotation_set.' + feature_type):
                    ID = IDbase + '-' + str(id_generator_dict[IDbase])
                    id_generator_dict[IDbase] = id_generator_dict[IDbase] + 1
            else:
                ID = IDbase
                id_generator_dict[IDbase] = 1
            other_attributes = {}
            other_attributes['evalue'] = fields[10]
            other_attributes['strand'] = strand
            parent = ID + '-match'
            eval('annotation_set.' + feature_type)[ID] = BaseAnnotation(ID, seqid, coords, feature_type, parent, other_attributes,
                                                                        annotation_set, create_parents_chain)
    if annotation_set_to_modify == None:
        return annotation_set


def calculate_heterozygosity(variant_set,locus_list = None, window = 10000):
    """calculates heterozygosity at each locus specified in the vcf_header associated with the variant set,
    or by a locus_list. Loci are specified in the locus list as either "seqid,seq_length" for entire
    contigs/scaffold, or for regions within contigs/scaffold, "seqid,start_position,stop_position" """
    outlist = []
    if locus_list == None:
        #generates locus list from vcf header if no locus list passed
        if variant_set.vcf_headers != None:
            locus_list = []
            for vcf_header_line in variant_set.vcf_headers[0].split('\n'):
                if "##contig=<ID=" in vcf_header_line:
                    seqid = vcf_header_line.split(',')[0][13:]
                    seqlen = int(vcf_header_line.split(',')[1][7:-1])
                    seqchunk_number = seqlen / window
                    for seqchunk in range(seqchunk_number):
                        locus = seqid + ',' + str(1 + window * seqchunk) + ',' + str(window * (seqchunk + 1))
                        locus_list.append(locus)
                    locus = seqid + ',' + str(1 + window * seqchunk_number) + ',' + str(seqlen)
                    locus_list.append(locus)
        else:
            print "function run with out locus_list, but variant_set has no vcf_header. One day I'll add a \
            function to get loci from a GenomeSequence; if you really want this, pester me about it on github 'Issues'"
            return None
    locus_list = list(set(locus_list))
    print "built locus list"    
    print len(locus_list)
    locus_het_count_dic = {}
    loci_dic = {}
    for locus in locus_list:
            locus_het_count_dic[locus] = {}
            for genotype in variant_set[list(variant_set)[0]].genotypes:
                locus_het_count_dic[locus][genotype] = 0
            seqid = locus.split(',')[0]
            if seqid in loci_dic:
                loci_dic[seqid].append(locus)
            else:
                loci_dic[seqid] = [locus]
    for variant_code in variant_set:
        variant_code_split = variant_code.split('<:>')
        seqid = variant_code_split[0]
        position = int(variant_code_split[1])
        for locus in loci_dic[seqid]:
            locus_split = locus.split(',')
            if len(locus.split(',')) > 2:
                if int(locus_split[1]) <= position <= int(locus_split[2]):
                    for genotype in variant_set[variant_code].genotypes:
                        genotypeGT = variant_set[variant_code].genotypes[genotype].GT
                        if genotypeGT[0] != genotypeGT[-1]:
                            locus_het_count_dic[locus][genotype] = locus_het_count_dic[locus][genotype] + 1
            else:
                if seqid == locus_split[0]:
                    for genotype in variant_set[variant_code].genotypes:
                        genotypeGT = variant_set[variant_code].genotypes[genotype].GT
                        if genotypeGT[0] != genotypeGT[-1]:
                            locus_het_count_dic[locus][genotype] = locus_het_count_dic[locus][genotype] + 1
    standard_genotype_list = None
    for locus in locus_list:
        if standard_genotype_list == None:
            standard_genotype_list = list(locus_het_count_dic[locus])
            print standard_genotype_list
        locus_split = locus.split(',')
        if len(locus.split(',')) > 2:
            seqlen = int(locus_split[2]) - int(locus_split[1]) + 1
        else:
            seqlen = int(locus_split[1])
        if seqlen < 1:
            pass
        else:
            hetrate_list = []
            for genotype in standard_genotype_list:
                hetrate_list.append(str( 100.0 * locus_het_count_dic[locus][genotype] / seqlen))
            outlist.append(locus + "," + ",".join(hetrate_list))
    return '\n'.join(outlist)
    

def read_vcf(vcf, variant_set_to_modify = None):
    """reads vcf file into variant_set"""
    vcf_list = read_to_string(vcf).split('\n')
    vcf_headerlines = []
    if variant_set_to_modify == None:
        variant_set = VariantSet()
    else:
        variant_set = variant_set_to_modify
    if variant_set.vcf_headers == None:
        variant_set.vcf_headers = []
    vcf_header_index = len(variant_set.vcf_headers)
    for line in vcf_list:
        if line == "":
            pass
        elif line[:2] == "##":
            vcf_headerlines.append(line)
        elif line[0] == "#":
            field_names = line[1:].split('\t')
            if len(field_names) > 8:
                sample_names = field_names[9:]
        else:
            fields = line.split('\t')
            seqid = fields[0]
            position = fields[1]
            ref_allele = fields[3]
            alt_alleles = fields[4].split(',')
            variant_ID = seqid + "<:>" + position
            variant_set[variant_ID] = Variant(ref_allele, alt_alleles, variant_set = variant_set)
            variant_set[variant_ID].ID = fields[2]
            variant_set[variant_ID].quality = fields[5]
            variant_set[variant_ID].filter_status = fields[6]
            variant_set[variant_ID].info = fields[7]
            variant_set[variant_ID].vcf_header_index = vcf_header_index
            if len(fields) > 8:
                genotypes = {}
                sample_features = fields[8].split(':')
                for sample in fields[9:]:
                    sample_name = sample_names[fields.index(sample) - 9]
                    genotypes[sample_name] = Genotype()
                    this_sample_features = sample.split(':')
                    for feature in sample_features:
                        try:
                            setattr(genotypes[sample_name], feature, this_sample_features[sample_features.index(feature)])
                        except IndexError:
                            pass
                variant_set[variant_ID].genotypes = copy.deepcopy(genotypes)
    variant_set.vcf_headers.append('\n'.join(vcf_headerlines))
    if variant_set_to_modify == None:
        return variant_set


# def write_gtf(annotation_set, keep_UTR_features = False, stop_codon = "none", start_codon = "none", outfeature = "CDS"):
#     """writes an annotation_set to a sensible version of the gtf (gene transfer file) format. This version will have only
#     non-overlapping features (i.e. no nested features) corresponding to base-level annotations- e.g. UTR, CDS OR exon (whichever
#     is passed via the "outfeature" option"), stop_codon, and start_codon. Inclusion of stop_codon and start_codon as seperate
#     from the CDS/exon feature is controlled by those options- either "none" or "force". Eventually there will be an autodetect
#     option to see if the first/last three nucleotides are start or stop codons based on the genome sequence, but don't hold your breath"""
#     gtf_lines = []
#     for CDS in annotation_set.CDS:
#         
    



class Genotype():
    """individual genotype to populate a GenotypeDict"""
    def name(self, ):
        pass
    

class Variant():
    """individual variants from reference genome sequence. Can be SNPs or polimorphism"""
    def __init__(self, ref_allele, alt_alleles, genotypes = None, variant_set = None, vcf_header_index = None):
        self.variant_set = variant_set
        self.ref_allele = ref_allele
        self.alt_alleles = alt_alleles
        self.genotypes = genotypes
    

class VariantSet(dict):
    """set of variants from reference genome sequence. Can be SNPs or polimorphism"""
    def __init__(self, genome = None, vcf_headers = None):
        self.genome = genome
        self.vcf_headers = vcf_headers
    

class AnnotationSet():
    """A set of annotations of a single genome. Each feature type (e.g. gene, transcript, exon, etc.)
    is stored in it's own dictionary as Annotations with their ID as their key (see "Annotation" class).
    The AnnotationSet itself also functions losely as a dictionary, in that any feature can be returned
    by indexing the AnnotationSet with the ID as a key (e.g. my_annotation_set["my_feature_ID"])"""
    def __init__(self, genome = None):
        self.gene = {}
        self.transcript = {}
        self.CDS = {}
        self.UTR = {}
        self.genome = genome
    
    def __getitem__(self,item):
        all_dicts = {}
        for attribute in dir(self):
            if type(eval("self." + attribute)) == dict:
                try:
                    all_dicts[item] = eval("self." + attribute)[item]
                except:
                    pass
        return all_dicts[item]
    
    def read_gff3(self, gff3, *args, **kwargs):
        kwargs["annotation_set_to_modify"] = self
        read_gff3(gff3, *args, **kwargs)
    
    def get_seqid(self, seqid):
        seqid_annotation_set = AnnotationSet()        
        for attribute in dir(self):
            if type(eval("self." + attribute)) == dict:
                setattr(seqid_annotation_set,attribute,{})
                for feature in eval('self.'+ attribute):
                    feature_obj = eval('self.' + attribute)[feature]
                    if feature_obj.seqid == seqid:
                        eval('seqid_annotation_set.' + feature_obj.feature_type)[feature] = feature_obj
        return seqid_annotation_set
    
    def get_all_seqids(self):
        seqid_list = []
        for attribute in dir(self):
            if type(eval("self." + attribute)) == dict:
                for feature in eval('self.'+ attribute):
                    seqid_list.append(eval('self.' + attribute)[feature].seqid)
        return list(set(seqid_list))
    
    def read_exonerate(self, exonerate_output):
        read_exonerate(exonerate_output,annotation_set_to_modify = self)
    
    def read_blast_csv(self, blast_csv, hierarchy = ['match','match_part'], source = 'blast', find_truncated_locname = False):
        read_blast_csv(blast_csv, annotation_set_to_modify = self, hierarchy = hierarchy, source = source, find_truncated_locname = find_truncated_locname)
    
    def read_cegma_gff(self, cegma_gff):
        read_cegma_gff(cegma_gff, annotation_set_to_modify = self)
    
    def get_fasta(self,feature,seq_type = "nucleotide",longest=False):
        fasta_list = []
        for annotation in eval('self.' + feature):
                fasta_list.append(eval('self.' + feature)[annotation].get_fasta(seq_type = seqtype,longest = longest))
        return "\n".join(fasta_list)
        
    

class BaseAnnotation():
    """Bottom-most level annotation on a genome, for example CDS, UTR, Match, etc. Anything that should have no children"""
    def __init__(self, ID, seqid, coords, feature_type, parent = None, other_attributes = {}, annotation_set = None,
                 create_parents_chain=['transcript','gene']):
        #Sets up most attributes
        self.ID = ID
        self.seqid = seqid
        self.coords = coords
        self.feature_type = feature_type
        self.annotation_set = annotation_set
        for attribute in other_attributes:
            setattr(self, attribute, other_attributes[attribute])
        #checks if feature type needs to be added to annotation_set
        if annotation_set != None:
            if not feature_type in annotation_set.__dict__:
                setattr(annotation_set,feature_type, {})
            #checks if parent feature types need to be added to annotation_set
            if create_parents_chain != None:
                for parent_feature_type in create_parents_chain:
                    if not parent_feature_type in annotation_set.__dict__:
                        setattr(annotation_set,parent_feature_type,{})
        #checks if parent features present:
            if parent == None:
                pass
            #checks if parent needs to be created
            elif parent in annotation_set.__dict__[create_parents_chain[0]]:
                self.parent = parent
                annotation_set.__dict__[create_parents_chain[0]][parent].child_list.append(ID)
            #Executes parent creation process if parent needs to be created
            else:
                #checks for strand in base annotation attributes since this needs to be passed up to parents
                if 'strand' in self.__dict__:
                    other_attributes = {'strand':self.strand}
                else:
                    other_attributes = {}
                #sets up hierarchy for parent creation
                hierarchy = {feature_type: create_parents_chain[0]}
                for feature_index in range(len(create_parents_chain))[:-1]:
                    hierarchy[create_parents_chain[feature_index]] = create_parents_chain[feature_index + 1]
                active_feature_type = feature_type
                active_feature_ID = ID
                if len(create_parents_chain) > 1:
                    self.parent = parent + '-' + create_parents_chain[0]
                else:
                    self.parent = parent
                parent_to_create = parent + '-' + hierarchy[active_feature_type]
                #checks if parent needs to be created and creates parent
                if len(create_parents_chain) > 1:
                    while not parent in annotation_set.__dict__[hierarchy[active_feature_type]] and not parent_to_create in annotation_set.__dict__[hierarchy[active_feature_type]]:
                        parent_to_create = parent + '-' + hierarchy[active_feature_type]
                        #checks whether this is second-to-last round of parent creation
                        if active_feature_type == create_parents_chain[-2]:
                            parent_to_create = parent
                            break
                        elif parent in annotation_set.__dict__[hierarchy[hierarchy[active_feature_type]]] or hierarchy[active_feature_type] == create_parents_chain[-2]:
                            next_level_parent = parent
                        else:
                            next_level_parent = parent + '-' + hierarchy[hierarchy[active_feature_type]]
                        #creates parent
                        annotation_set.__dict__[hierarchy[active_feature_type]][parent_to_create] = ParentAnnotation(ID = parent_to_create,
                                                                                                                     seqid = seqid,
                                                                                                                     feature_type = hierarchy[active_feature_type],
                                                                                                                     child_list = [active_feature_ID],
                                                                                                                     parent = next_level_parent,
                                                                                                                     annotation_set = annotation_set, other_attributes = other_attributes)
                        #resets active feature type and ID
                        active_feature_type = hierarchy[active_feature_type]
                        active_feature_ID = parent_to_create
                #checks if parent was found or last-level parent needs to be created
                try:
                    annotation_set.__dict__[hierarchy[active_feature_type]][parent]
                except KeyError:
                    try:
                        annotation_set.__dict__[hierarchy[active_feature_type]][parent_to_create].child_list.append(ID)
                    except KeyError:
                        annotation_set.__dict__[hierarchy[active_feature_type]][parent] = ParentAnnotation(ID = parent, seqid = seqid,
                                                                                                       feature_type = hierarchy[active_feature_type],
                                                                                                       child_list = [active_feature_ID],parent = None,
                                                                                                       annotation_set = annotation_set, other_attributes = other_attributes)
    def get_coords(self):
        return self.coords
    
    def get_seq(self):
        try:
            if self.strand == '+':
                return Sequence(self.annotation_set.genome.genome_sequence[self.seqid][self.coords[0]-1:self.coords[1]])
            elif self.strand == '-':
                return Sequence(self.annotation_set.genome.genome_sequence[self.seqid][self.coords[0]-1:self.coords[1]]).reverse_compliment()
        except:
            print "either base_annotation has not annotation_set, or annotation_set has no genome, or genome has no\
            genome sequence, or genome sequence has no matching seqid, or coords are out of range on that seqid"
            print self.seqid


class ParentAnnotation():
    """Parent of any BaseAnnotation. Examples include genes and transcripts. Suggested hierarchy for genes is
    CDS (as BaseAnnotation) -> transcript -> gene."""
    def __init__(self, ID, seqid, feature_type, child_list = [], parent = None, annotation_set = None, other_attributes = {}):
        self.ID = ID
        self.seqid = seqid
        self.feature_type = feature_type
        self.child_list = copy.copy(child_list)
        self.parent = parent
        self.annotation_set = annotation_set
        for attribute in other_attributes:
            setattr(self, attribute, other_attributes[attribute])
        if annotation_set != None:
            try:
                annotation_set[parent].child_list.append(ID)
            except:
                pass
    
    def get_coords(self):
        if len(self.child_list) > 0 and self.annotation_set != None:
            coords_list = []
            for child in self.child_list:
                child_object = self.annotation_set[child]
                if child_object.__class__.__name__ == 'ParentAnnotation':
                    coords_list = coords_list + list(child_object.get_coords())
                elif child_object.__class__.__name__ == 'BaseAnnotation':
                    coords_list = coords_list + list(child_object.coords)
                else:
                    print "for some reason you have children in ParentAnnotation " + self.ID + " which are neither \
                    ParentAnnotation objects nor BaseAnnotation object. Get your act together"
            return (min(coords_list),max(coords_list))
    
    def get_fasta(self, seq_type = "nucleotide", longest=False):
        """Returns fasta of this annotation's sequence. If this feature has multiple subfeatures (e.g. this is a gene
        and it has multiple transcripts), the sequence of each subfeature will be an entry in the fasta string."""
        if len(self.child_list) > 0 and self.annotation_set != None:
            if self.annotation_set.genome != None:
                fasta_list = []
                child_type = self.annotation_set[self.child_list[0]].__class__.__name__
                if child_type == 'BaseAnnotation':
                    seq_list = []
                    child_dict = {}
                    for child in self.child_list:
                        child_obj = self.annotation_set[child]
                        child_dict[child_obj.coords] = child_obj.get_seq()
                        strand = child_obj.strand
                    children_in_correct_order = list(child_dict)
                    children_in_correct_order.sort()
                    if strand == '-':
                        children_in_correct_order.reverse()
                    for child in children_in_correct_order:
                        seq_list.append(child_dict[child])
                    if seq_type == "nucleotide":
                        new_seq = Sequence("".join(seq_list))
                    elif seq_type == "protein":
                        new_seq = Sequence("".join(seq_list)).translate()
                    else:
                        print seq_type + ' is not valid seq_type. Please specify "protein" or "nucleotide".'
                    fasta_list.append('>' + self.ID + '\n' + new_seq)
                else:
                    for child in self.child_list:
                        fasta_list.append(self.annotation_set[child].get_fasta(seq_type=seq_type))
                if longest == True:
                    seqlens = {}
                    for seq in fasta_list:
                        seqlens[len("".join(seq.split('\n')[1:]))] = seq
                    return seqlens[max(list(seqlens))]
                else:
                    return '\n'.join(fasta_list)
    

class Sequence(str):
    """DNA sequence. Has methods allowing reverse complimenting,
        translating, etc."""
    def reverse_compliment(self):
        """returns reverse compliment of self"""
        new_sequence_list = []
        compliment_dict = {'a':'t','t':'a','g':'c','c':'g','A':'T','T':'A','G':'C','C':'G','n':'n','N':'N','-':'-'}
        for residue in self[::-1]:
            try:
                new_sequence_list.append(compliment_dict[residue])
            except KeyError:
                new_sequence_list.append('n')
        return Sequence(''.join(new_sequence_list))
    
    def translate(self,library = {'TTT':'F','TTC':'F','TTA':'L','TTG':'L','CTT':'L','CTC':'L','CTA':'L','CTG':'L',
                                  'ATT':'I','ATC':'I','ATA':'I','ATG':'M','GTT':'V','GTC':'V','GTA':'V','GTG':'V',
                                  'TCT':'S','TCC':'S','TCA':'S','TCG':'S','CCT':'P','CCC':'P','CCA':'P','CCG':'P',
                                  'ACT':'T','ACC':'T','ACA':'T','ACG':'T','GCT':'A','GCC':'A','GCA':'A','GCG':'A',
                                  'TAT':'Y','TAC':'Y','TAA':'*','TAG':'*','CAT':'H','CAC':'H','CAA':'Q','CAG':'Q',
                                  'AAT':'N','AAC':'N','AAA':'K','AAG':'K','GAT':'D','GAC':'D','GAA':'E','GAG':'E',
                                  'TGT':'C','TGC':'C','TGA':'*','TGG':'W','CGT':'R','CGC':'R','CGA':'R','CGG':'R',
                                  'AGT':'S','AGC':'S','AGA':'R','AGG':'R','GGT':'G','GGC':'G','GGA':'G','GGG':'G'},
                  frame = 0, strand = '+',trimX = True):
        triplet = ""
        newseq = ""
        if strand == '+':
            seq = self
        elif strand == '-':
            seq = self.reverse_compliment()
        if len(seq) > (2 + frame):
            for residue_position in range(frame, len(self)):
                triplet = triplet + seq[residue_position].upper()
                if (residue_position + frame) % 3 == 2:
                    try:
                        newseq = newseq + library[triplet]
                    except KeyError:
                        newseq = newseq + 'X'
                    triplet = ""
            if trimX:
                if newseq[0] == 'X':
                    newseq = newseq[1:]
            return newseq
    
    def get_orfs(self, longest = False, strand = 'both', from_atg = False):
        orflist = []
        if longest:
            candidate_list = []
            longest_orf_len = 0
        for frame in [0,1,2]:
            for strand in ['-','+']:
                translated_seq = self.translate(frame=frame,strand=strand)
                if translated_seq:
                    translated_seq_list = translated_seq.split('*')
                    for orf in translated_seq_list:
                        if from_atg:
                            try:
                                output_orf = 'M' + ''.join(orf.split('M')[1:])
                            except IndexError:
                                continue
                        else:
                            output_orf = orf
                        if longest:
                            if len(output_orf) > longest_orf_len:
                                candidate_list.append(output_orf)
                                longest_orf_len = len(output_orf)
                        else:
                            orflist.append(output_orf)
        if longest:
            return candidate_list[-1]
        else:
            return orflist


class GenomeSequence(dict):
    """genome sequence class, currently takes input in multi-fasta format."""
    def __init__(self,genome_sequence = None):
        #reads input file location, file, or string
        sequence_string = read_to_string(genome_sequence)
        #breaks sequence into sequence blocks (contigs, scaffolds, or chromosomes), adds sequence 
        #   from each block as dictionary entry into self with block name as key.
        if sequence_string != None:
            for locus in sequence_string.split('>')[1:]:
                block = locus.split('\n')
                seqid = block[0]
                seqstring = Sequence("".join(block[1:]))
                self[seqid] = seqstring

    


class Genome():
    """genome class, which contains sequence and annotations. Annotations can be given as annotation_set object, gff3, cegma_gff,
    blast_csv, or exonerate_output (just set annotation_format)."""
    def __init__(self,genome_sequence = None, annotations = None, varients = None, annotation_format = 'annotation_set'):
        if genome_sequence.__class__.__name__ == 'GenomeSequence' or genome_sequence == None:
            self.genome_sequence = genome_sequence
        else:
            self.genome_sequence = GenomeSequence(genome_sequence)
        if annotations != None:
            if annotations.__class__.__name__ == "AnotationSet" and annotation_format == 'annotation_set':
                self.annotations = annotations
                self.annotations.genome = self
            elif annotation_format == 'gff3':
                self.annotations = read_gff3(annotations)
                self.annotations.genome = self
            elif annotation_format == 'cegma_gff':
                self.annotations = read_cegma_gff(annotations)
                self.annotations.genome = self
            elif annotation_format == 'blast_csv':
                self.annotations = read_blast_csv(annotations)
                self.annotations.genome = self
            elif annotation_format == 'exonerate_output':
                self.annotations = read_exonerate(annotations)
                self.annotations.genome = self
        else:
            self.annotations = annotations
    
    def get_scaffold_fasta(self, seqid):
        return '>' + seqid + '\n' + self.genome_sequence[seqid]
    
    def get_genome_fasta(self, remove_spaces = False):
        fasta_list = []
        for seqid in self.genome_sequence:
            if remove_spaces:
                fasta_header = seqid.split()[0]
            else:
                fasta_header = seqid
            fasta_list.append('>' + fasta_header + '\n' + self.genome_sequence[seqid])
        return "\n".join(fasta_list)
    
    def write_apollo_gff(self, seqid, suppress_fasta = False):
        if self.genome_sequence != None and self.annotations != None:
            try:
                apollo_gff = write_longform_gff(self.annotations.get_seqid(seqid))
                if not suppress_fasta:
                    apollo_gff = apollo_gff + '\n' + self.get_scaffold_fasta(seqid)
                return apollo_gff
            except:
                if not suppress_fasta:
                    return self.get_scaffold_fasta(seqid)
                else:
                    return ""
        else:
            print "genome object is either missing genome_sequence or annotations"
    
    def get_seqids(self, from_annotations = False):
        seqid_list = []
        warning = False
        if self.genome_sequence != None:
            for seqid in self.genome_sequence:
                seqid_list.append(seqid)
        if self.annotations != None and from_annotations:
            for seqid in self.annotations.get_all_seqids():
                if seqid not in seqid_list:
                    seqid_list.append(seqid)
                    warning = True
        if warning:
            print "warning, some annotations possessed seqids not found in sequence dictionary"
        return seqid_list
    
    def read_exonerate(self, exonerate_output):
        if self.annotations != None:
            self.annotations.read_exonerate(exonerate_output)
        else:
            self.annotations = read_exonerate(exonerate_output)
            self.annotations.genome = self
    
    def read_blast_csv(self, blast_csv, hierarchy = ['match','match_part'], source = 'blast', find_truncated_locname = False):
        if self.annotations == None:
            self.annotations = AnnotationSet()
            self.annotations.genome = self
        self.annotations.read_blast_csv(blast_csv, hierarchy = hierarchy, source = source, find_truncated_locname = find_truncated_locname)
    
    def read_cegma_gff(self, cegma_gff):
        if self.annotations != None:
            self.annotations.read_cegma_gff(cegma_gff)
        else:
            self.annotations = read_cegma_gff(cegma_gff)
            self.annotations.genome = self

    def read_gff3(self, gff3, *args, **kwargs):
        if self.annotations != None:
            self.annotations.read_gff3(gff3, *args, **kwargs)
        else:
            self.annotations = read_gff3(gff3, *args, **kwargs)
            self.annotations.genome = self
    
    def read_vcf(self, vcf):
        self.variants = read_vcf(vcf)
    

class position_dic(dict):
    def __init__(self, genome_sequence):
        for seqid in genome_sequence:
            self[seqid] = []
            for position in range(len(genome_sequence[seqid])):
                self[seqid].append(0)

    def fill_from_annotations(self, annotation_set,feature,genome_sequence, fill_type = "coords"):
        """will eventually accept "start" instead of "coords" for fill_type"""
        for annotation in eval("annotation_set." + feature):
            annotation_obj = eval("annotation_set." + feature)[annotation]
            seqid = annotation_obj.seqid
            coords = annotation_obj.get_coords()
            for position in range(coords[0],coords[1] + 1):
                self[seqid][position] = 1

    def sliding_window_calculate(self, window_size, operation="sum"):
        new_dic = {}
        for seqid in self:
            new_dic[seqid] = []
            for position in self[seqid][:-1*window_size]:
                val_list = self[seqid][position:position + window_size]
                if operation == "sum":
                    new_dic[seqid].append(sum(val_list))
                elif operation == "average":
                    new_dic[seqid].append(sum(val_list) * 1.0 / len(val_list))
        return(copy.deepcopy(new_dic))

