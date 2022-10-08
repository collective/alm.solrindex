# This is derived from collective.solr.queryparser.
# See http://lucene.apache.org/java/2_4_0/queryparsersyntax.html

from re import compile


# Solr/lucene reserved characters/terms: + - && || ! ( ) { } [ ] ^ " ~ * ? : \
# Five groups for tokenizer:
# 1) Whitespace (\s+)
# 2) Any non reserved chars (normal text) ([^(){}\[\]+\-!^\"~*?:\\&|\s]+)
# 3) Any grouping characters ([(){}\[\]"])
# 4) Any special operators ([+\-!^~*?:\\]|&&|\|\|))
# 5) Special characters not used in operators ([&|])
query_tokenizer = compile(
    r"(?:"
    r"(\s+)|"
    r'([^(){}\[\]+\-!^"~*?:\\&|\s]+)|'
    r'([(){}\[\]"])|'
    r"([+\-!^~*?:\\]|&&|\|\|)|"
    r"([&|])"
    r")"
)


class Whitespace:
    def __bool__(self):
        return False

    def __str__(self):
        return " "


class Group(list):
    def __init__(self, start=None, end=None):
        self.start = start
        self.end = end
        # Set on pop
        self.isgroup = False

    def __str__(self):
        res = [x for x in self if x]
        lenres = len(res)
        if lenres == 0:
            return ""
        elif lenres == 1:
            return str(res[0])
        # Otherwise, also print whitespace
        return "%s%s%s" % (self.start, "".join(str(x) for x in self), self.end)


class Quote(Group):
    def __str__(self):
        if not self.end:
            # No finishing quote, we have to add new group if there is
            # whitespace
            if [x for x in self if isinstance(x, Whitespace)]:
                self.start = "(%s" % self.start
                self.end = ")"
        return "%s%s%s" % (self.start, "".join(str(x) for x in self), self.end)


class Range(Group):
    def __str__(self):
        first = last = "*"
        if len(self) == 0:
            return ""
        if "TO" not in self:
            # Not valid range, quote
            return "\\%s%s\\%s" % (self.start, "".join(str(x) for x in self), self.end)
        else:
            # split on 'TO'
            split = self.index("TO")
            if split > 0:
                first = "".join(
                    str(x) for x in self[:split] if not isinstance(x, Whitespace)
                )
            if split < (len(self) - 1):
                last = "".join(
                    str(x) for x in self[split + 1 :] if not isinstance(x, Whitespace)
                )
        return "%s%s TO %s%s" % (self.start, first, last, self.end)


class Stack(list):
    def __init__(self):
        self.append([])

    def add(self, item):
        self.current.append(item)
        self.append(item)

    @property
    def current(self):
        return self[-1]

    def __str__(self):
        return "".join(str(x) for x in self[0])

    def __unicode__(self):
        return "".join(str(x) for x in self[0])


def quote_query(query):
    """Parse a field-specific query and return a quoted version.

    For example, 'foo bar' is converted to '(foo bar)'.
    """
    stack = Stack()
    raw_tokens = query_tokenizer.findall(query.strip())

    # fold token[4] into token[1]
    tokens = []
    for token in raw_tokens:
        if token[4]:
            token = token[:1] + token[4:5] + token[2:4]
        else:
            token = token[:4]
        tokens.append(token)

    # Counter enables lookahead
    i = 0
    stop = len(tokens)
    while i < stop:
        whitespace, text, grouping, special = tokens[i]

        if whitespace:
            # Add whitespace if group text, range and group filter on display
            if isinstance(stack.current, Group):
                stack.current.append(Whitespace())
            elif isinstance(stack.current, list):
                # We have whitespace with no grouping, insert group
                new = Group("(", ")")
                new.extend(stack.current)
                new.append(Whitespace())
                stack.current[:] = []
                stack.add(new)

        elif grouping:
            # [] (inclusive range), {} (exclusive range), always with
            # TO inside; () group
            # "" for quotes
            # NOTE: Solr does not support mixed inclusive/exclusive range,
            # but probably will in the future.  See
            # http://issues.apache.org/jira/browse/SOLR-355
            if grouping == '"':
                if isinstance(stack.current, Quote):
                    # Handle empty double quote
                    if not stack.current:
                        stack.current.end = r"\""
                    else:
                        stack.current.start = stack.current.end = '"'
                        stack.current.isgroup = True
                    stack.pop()
                else:
                    # Right now this is just a single quote,
                    # we set proper start and end before popping
                    new = Quote(start=r"\"", end="")
                    stack.add(new)
            elif isinstance(stack.current, Quote):
                # If we're in a quote, escape and print
                stack.current.append(r"\%s" % grouping)
            elif grouping in "[{":
                new = Range(start=grouping, end={"[": "]", "{": "}"}[grouping])
                stack.add(new)
            elif grouping == "(":
                new = Group(start="(", end=")")
                stack.add(new)
            elif grouping in "]})":
                if isinstance(stack.current, Group) and stack.current.end == grouping:
                    stack.current.isgroup = True
                    stack.pop()
                else:
                    stack.current.append(r"\%s" % grouping)

        elif text:
            stack.current.append(text)

        elif special:
            if special == "\\":
                # Inspect next to see if it's quoted special or quoted group
                if i + 1 < stop:
                    _, _, g2, s2 = tokens[i + 1]
                    if s2:
                        stack.current.append("%s%s" % (special, s2))
                        # Jump ahead
                        i += 1
                    elif g2:
                        stack.current.append("%s%s" % (special, g2))
                        # Jump ahead
                        i += 1
                    else:
                        # Quote it
                        stack.current.append("\\%s" % special)
                else:
                    # Quote it
                    stack.current.append(r"\\")
            elif isinstance(stack.current, Quote):
                stack.current.append(r"\%s" % special)
            elif special in "+-":
                if i + 1 < stop:
                    _, t2, g2, _ = tokens[i + 1]
                    # We allow + and - in front of phrase and text
                    if t2 or g2 == '"':
                        stack.current.append(special)
                    else:
                        # Quote it
                        stack.current.append("\\%s" % special)
            elif special in "~^":
                # Fuzzy or proximity is always after a term or phrase,
                # and sometimes before int or float like roam~0.8 or
                # "jakarta apache"~10
                if i > 0:
                    _, t0, g0, _ = tokens[i - 1]
                    if t0 or g0 == '"':
                        # Look ahead to check for integer or float

                        if i + 1 < stop:
                            _, t2, _, _ = tokens[i + 1]
                            # float(t2) might fail
                            try:
                                if t2 and float(t2):
                                    stack.current.append("%s%s" % (special, t2))
                                    # Jump ahead
                                    i += 1
                                else:
                                    stack.current.append(special)
                            except ValueError:
                                stack.current.append(special)
                        # (i + 1) < stop
                        else:
                            stack.current.append(special)
                    # t0 or g0 == '"'
                    else:
                        stack.current.append("\\%s" % special)
                # i > 0
                else:
                    stack.current.append("\\%s" % special)
            elif special in "?*":
                # ? and * can not be the first characters of a search
                if (
                    stack.current
                    and not getattr(stack.current[-1], "isgroup", False)
                    and (
                        isinstance(stack.current[-1], (str, bytes))
                        and not stack.current[-1] in special
                    )
                ) or isinstance(stack.current, Range):
                    stack.current.append(special)
            elif isinstance(stack.current, Group):
                stack.current.append(special)
            elif isinstance(stack.current, list):
                stack.current.append("\\%s" % special)
        i += 1
    return str(stack)
