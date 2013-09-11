from pyfits import Header
from pyfits import PrimaryHDU

class FITSKeyword(object):
    """
    Represents a FITS keyword.

    Useful if one logical keyword (e.g. `airmass`) has several
    often-used synonyms (e.g. secz and `airmass`).

    Checks whether the keyword is a valid FITS keyword when initialized.
    """
    def __init__(self, name=None, value=None, comment=None, synonyms=None):
        """
        All inputs are optional.
        """
        self._hdr = Header()
        self.name = name
        self.value = value
        self.comment = comment
        if synonyms is None:
            self.synonyms = []
        else:
            self.synonyms = synonyms
        return

    def __str__(self):
        if self.value is None:
            value_string = ''
        else:
            value_string = str(self.value)
        return ("%s = %s    / %s \n with synonyms: %s" %
                (self.name.upper(), value_string, self.comment,
                 ",".join(str(syn).upper() for syn in self.synonyms)))

    def _set_keyword_case(self, keyword):
        return keyword.upper()

    @property
    def name(self):
        """
        Primary name of the keyword.
        """
        return self._name

    @name.setter
    def name(self, keyword_name):
        if self._keyword_is_valid(keyword_name):
            self._name = self._set_keyword_case(keyword_name)

    @property
    def synonyms(self):
        """
        List of synonyms for the keyword.
        """
        return self._synonyms

    @synonyms.setter
    def synonyms(self, inp_synonyms):
        self._synonyms = []
        if isinstance(inp_synonyms, basestring):
            synonym_list = [inp_synonyms]
        elif isinstance(inp_synonyms, list):
            synonym_list = inp_synonyms
        else:
            raise ValueError(
                'Synonyms must either be a string or a list of strings')
        for synonym in synonym_list:
            if self._keyword_is_valid(synonym):
                self._synonyms.append(self._set_keyword_case(synonym))
        return

    def _keyword_is_valid(self, keyword_name):
        if keyword_name is not None:
            dummy_value = 0
            try:
                self._hdr[keyword_name] = dummy_value
            except ValueError:
                raise
            return True
        else:
            return False

    @property
    def names(self):
        """
        All names, including synonyms, for this keyword, as a list.
        """
        all_names = [self.name]
        if self.synonyms:
            all_names.extend(self.synonyms)
        return all_names

    def historyComment(self, with_name=None):
        """
        Method to add HISTORY line to header.
        Use `with_name` to override the name of the keyword object.
        """
        if with_name is None: with_name = self.name
        return "Updated keyword %s to value %s" % (with_name.upper(), self.value)

    def addToHeader(self, hdu_or_header, with_synonyms=True, history=False):
        """
        Method to add keyword to FITS header.

        `hdu_or_header` can be either a pyfits `PrimaryHDU` or a
        pytfits `Header` object.
        `with_synonyms` determines whether the keyword's synonynms are
        also added to the header.j
        `history` determines whether a history comment is added when
        the keyword is added to the header.
        """
        if isinstance(hdu_or_header, PrimaryHDU):
            header = hdu_or_header.header
        elif isinstance(hdu_or_header, Header):
            header = hdu_or_header
        else:
            raise ValueError('argument must be a fits Primary HDU or header')

        header[self.name] = (self.value, self.comment)
        if history:
            header.add_history(self.historyComment())
        if with_synonyms and self.synonyms:
            for synonym in self.synonyms:
                header[synonym] = (self.value, self.comment)
                if history:
                    header.add_history(self.historyComment(with_name=synonym))

    def setValueFromHeader(self, hdu_or_header):
        """
        Determine value of keyword from FITS header.

        `hdu_or_header` can be either a pyfits `PrimaryHDU` or a
        pytfits `Header` object.

        If both the primary name of the keyword and its synonyms are
        present in the FITS header, checks whether the values are
        identical, and if they aren't, raises an error.
        """
        if isinstance(hdu_or_header, PrimaryHDU):
            header = hdu_or_header.header
        elif isinstance(hdu_or_header, Header):
            header = hdu_or_header
        else:
            raise ValueError('argument must be a fits Primary HDU or header')
        values = []
        for name in self.names:
            try:
                values.append(header[name])
            except KeyError:
                continue
        if values:
            if len(set(values)) > 1:
                raise ValueError('Found more than one value for keyword %s:\n Values found are: %s'
                                 % (','.join(self.names), ','.join(values)))
            self.value = values[0]
        else:
            raise ValueError('Keyword not found in header: %s' % self)
        
                        

