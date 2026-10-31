"""Full unittest discovery with bounded CI failure annotations, never filters.

Normal unittest tracebacks/results remain intact. Only the additional GitHub
annotation is sanitized; it contains the test ID and exception summary only.
"""
import os
import re
import sys
import unittest


def safe_annotation(value):
    try:text=str(value)[:8192]
    except Exception:text='<unprintable>'
    text=re.sub(r'(?i)\b[a-z][a-z0-9+.-]*://[^\s]+','[URL REDACTED]',text)
    text=re.sub(r'(?i)\b(?:authorization\s*[:=]\s*)?(?:bearer|basic)\s+[^\s,;]+','[AUTH REDACTED]',text)
    text=re.sub(r'''(?ix)\b(password|passwd|pwd|token|secret|client[_-]?secret|private[_-]?key|api[_-]?key|access[_-]?key|credential|authorization|cookie|username|user)\s*[:=]\s*(?:"[^"\r\n]*"|'[^'\r\n]*'|[^\s,;]+)''',r'\1=[REDACTED]',text)
    text=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]','?',text)
    # Limit after escaping too: '%' could otherwise triple the output size.
    return text.replace('%','%25').replace('\r','%0D').replace('\n','%0A')[:1800]


class AnnotationResult(unittest.TextTestResult):
    def annotate(self,test,error):
        if os.environ.get('GITHUB_ACTIONS')!='true':return
        try:message=str(error[1])
        except Exception:message='<unprintable>'
        summary='{}: {}: {}'.format(test.id(),error[0].__name__,message)
        self.stream.write('\n::error::unittest '+safe_annotation(summary)+'\n')
        self.stream.flush()
    def addError(self,test,err):
        self.annotate(test,err)
        super().addError(test,err)
    def addFailure(self,test,err):
        self.annotate(test,err)
        super().addFailure(test,err)
    def addSubTest(self,test,subtest,err):
        if err is not None:self.annotate(subtest,err)
        super().addSubTest(test,subtest,err)


def main():
    # Match `python -m unittest discover -s tests -v` import roots.
    sys.path.insert(0,os.getcwd())
    suite=unittest.defaultTestLoader.discover('tests')
    result=unittest.TextTestRunner(verbosity=2,resultclass=AnnotationResult).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
