import xml.etree.ElementTree as ET
import re
from functools import cached_property


class DataProcessor:
    def __init__(self, logger):
        self._logger = logger

    @cached_property
    def nsmap(self):
        return {
            'atom': 'http://www.w3.org/2005/Atom',
            'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
            'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata'
        }

    def sanitize_xml(self, xml_data):
        """Sanitize XML data by removing invalid characters."""
        if not isinstance(xml_data, str):
            raise TypeError(f"Expected string for XML data but got {type(xml_data)}")

        # Remove null bytes and specific invalid character references
        xml_data = xml_data.replace('\x00', '')
        xml_data = re.sub(r'&#x[0-9A-Fa-f]+;', '', xml_data)

        # Regular expression to remove other invalid XML characters
        invalid_xml_char_pattern = re.compile(
            r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\uFDD0-\uFDEF\uFFFE\uFFFF]|'
            r'[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]'
        )
        # Substitute invalid characters with an empty string
        return invalid_xml_char_pattern.sub('', xml_data)

    def parse_xml(self, xml_data: str):
        """
        Parse the given XML data and return a list of dictionaries representing the records.
        """
        try:
            sanitized_xml_data = self.sanitize_xml(xml_data)
            root = ET.fromstring(sanitized_xml_data)
            entries = []
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                record = {}
                for prop in entry.findall(".//m:properties/*", namespaces=self.nsmap):
                    tag_name = prop.tag.split("}")[1]  # Remove namespace
                    record[tag_name] = prop.text
                entries.append(record)
            self._logger.info(f"Parsed {len(entries)} records from the XML data.")
            return entries
        except ET.ParseError as e:
            self._logger.error(f"Failed to parse XML data: {e}")
            raise ValueError("Invalid XML data provided.")

    def get_xml_text(self, parent, tag_name):
        """Helper function to extract text from XML elements."""
        element = parent.find(f'd:{tag_name}', namespaces=self.nsmap)
        if element is not None and element.get('{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}null') != 'true':
            return element.text
        return None

    def get_xml_bool(self, value: str) -> bool:
        """Helper function to convert string value to boolean."""
        return value.lower() == 'true' if value else False

    def get_xml_float(self, parent, tag_name):
        """Helper function to extract float values from XML elements."""
        text_value = self.get_xml_text(parent, tag_name)
        try:
            return float(text_value) if text_value else None
        except ValueError:
            self._logger.warning(f"Could not convert '{text_value}' to float for tag '{tag_name}'")
            return None

    async def process_objects(self, xml_data, batch_size):
        """
        Process the XML data and perform necessary operations.
        This is a placeholder implementation. Replace with actual logic.
        """
        self._logger.info(f"Processing {len(xml_data)} records in batches of {batch_size}.")
        # ...process the data...
        return len(xml_data)  # Return the number of processed records
