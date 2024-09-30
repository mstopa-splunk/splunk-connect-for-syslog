from openai import OpenAI

try:
    import syslogng
    from syslogng import LogParser
except Exception:
    class LogParser:
        pass


class AIImportanceParser(LogParser):
    def init(self, options):
        self.client = OpenAI()
        return True

    def parse(self, log_message):
        """
        Label logs as `critical`, `important`, `neutral`, or `noise`.
        """
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a log importance tagger. You can return only one of the following tags: `critical`, `important`, `neutral`, or `noise`. Always return a tag and only one tag."
                    },
                    {
                        "role": "user",
                        "content": f"{log_message['MESSAGE']}"
                    }
                ]
            )

            tag = completion.choices[0].message.content
            if tag not in ['critical', 'important', 'neutral', 'noise']:
                return False
            log_message['IMPORTANCE'] = tag

        except:
            return False
        
        # return True, other way message is dropped
        return True