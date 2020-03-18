import os
from glob import glob

import click

import xmltodict
import json

from collections import OrderedDict

from tqdm import tqdm
from multiprocessing import Pool

from typing import List, Optional


def xml_path_to_dict(xml_file_path: str) -> OrderedDict:
    with open(xml_file_path, 'r') as xml_file:
        data: str = xml_file.read()

    return xmltodict.parse(data)


def convert_xml_file_to_json(xml_file_path: str, delete_xmls: bool):
    values_dict: OrderedDict = xml_path_to_dict(xml_file_path)
    json_string: str = json.dumps(values_dict, sort_keys=True, indent=4)

    json_file_path: str = xml_file_path.split('.')[0] + '.json'

    with open(json_file_path, 'w+') as json_file:
        json_file.write(json_string)

    if delete_xmls:
        os.remove(xml_file_path)


def is_filename_hidden(filename: str) -> bool:
    return filename[0] == '.' and len(filename) > 1


def is_file_within_legal_depth(root_dir: str, file: str, recursion_depth: Optional[int]) -> bool:
    return recursion_depth is None or len(file.split('\\')) - len(root_dir.split('\\')) <= recursion_depth


def all_xmls(root_directory_path: str, recursion_depth: Optional[int]) -> str:
    for root, dirs, files in os.walk(root_directory_path):
        sub_dirs_to_remove: List[str] = [sub_dir for sub_dir in dirs if
                                         is_filename_hidden(sub_dir.split('\\')[-1]) or not is_file_within_legal_depth(
                                             root_directory_path, r"{}\{}".format(root, sub_dir), recursion_depth)]

        for sub_dir_to_remove in sub_dirs_to_remove:
            dirs.remove(sub_dir_to_remove)

        for xml_file_name in filter(lambda file: file.endswith('.xml'), files):
            yield r"{}\{}".format(root, xml_file_name)


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('-r', '--recursion-depth', 'recursion_depth', type=click.INT, default=None,
              help="""The depth of the recursion, unlimited by default,
              use a value of 0 for no recursion (i.e only in the PATH directory)""")
@click.option('-d', '--delete-xmls', 'delete_xmls', is_flag=True,
              help="Whether or not we want to delete the xml files after the conversion")
@click.option('-w', '--num-workers', 'num_workers', type=click.IntRange(1, 20), default=1,
              help="The number of workers that will calculate the means and stds of the pictures")
def convert_xml_files_to_json(path: str, recursion_depth: Optional[int], delete_xmls: bool, num_workers: int):
    """
    converts XML files to JSON files

    PATH the path to either the file you want to convert or the directory where you want to convert all files
    """

    if os.path.isdir(path):
        to_convert = list(all_xmls(path, recursion_depth))

        if len(to_convert) == 0:
            raise Exception("ERROR: No XML files found!")

        pool = Pool(num_workers)
        pbar = tqdm(desc="XML to JSON Conversion Progress", total=len(to_convert))
        for xml_file in to_convert:
            pool.apply_async(convert_xml_file_to_json, args=(xml_file, delete_xmls), callback=lambda _: pbar.update())
        pool.close()
        pool.join()
        pbar.close()

    elif path.endswith('.xml'):
        convert_xml_file_to_json(path)

    else:
        raise Exception("ERROR: The inputted path in neither a directory nor an XML file!")

    print("Conversion complete!")


if __name__ == '__main__':
    convert_xml_files_to_json()
