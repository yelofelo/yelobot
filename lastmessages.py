class LastMessages:
    def __init__(self):
        self.channels = dict()

    def resend(self, message, channel_id, user_id):
        if channel_id in self.channels:
            prev_message, count, prev_user = self.channels[channel_id]
            
            if prev_message == message and prev_user != user_id:
                new_count = count + 1
                self.channels[channel_id] = (message, new_count, user_id)

                if new_count == 3:
                    return True

                return False


        self.channels[channel_id] = (message, 1, user_id)
        return False