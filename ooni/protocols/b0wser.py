from ooni.utils import log

class Mutator:
    idx = 0
    step = 0

    waiting = False
    waiting_step = 0

    def __init__(self, steps):
        """
        @param steps: array of dicts containing as keys data and wait. Data is
                      the content of the ith packet to be sent and wait is how
                      much we should wait before mutating the packet of the
                      next step.
        """
        self.steps = steps

    def _mutate(self, data, idx):
        """
        Mutate the idx bytes by increasing it's value by one

        @param data: the data to be mutated.

        @param idx: what byte should be mutated.
        """
        print "idx: %s, data: %s" % (idx, data)
        ret = data[:idx]
        ret += chr(ord(data[idx]) + 1)
        ret += data[idx+1:]
        return ret

    def state(self):
        """
        Return the current mutation state. As in what bytes are being mutated.

        Returns a dict containg the packet index and the step number.
        """
        return {'idx': self.idx, 'step': self.step}

    def next_mutation(self):
        """
        Increases by one the mutation state.

        ex. (* is the mutation state, i.e. the byte to be mutated)
        before [___*] [____]
               step1   step2
        after  [____] [*___]

        Should be called every time you need to proceed onto the next mutation.
        It changes the internal state of the mutator to that of the next
        mutatation.

        returns True if another mutation is available.
        returns False if all the possible mutations have been done.
        """
        if self.step > len(self.steps):
            self.waiting = True
            return False

        self.idx += 1
        current_idx = self.idx
        current_step = self.step
        current_data = self.steps[current_step]['data']
        data_to_receive = self.steps[current_step]['wait']

        if self.waiting and self.waiting_step == data_to_receive:
            log.debug("I am no longer waiting.")
            self.waiting = False
            self.waiting_step = 0
            self.idx = 0

        elif self.waiting:
            log.debug("Waiting some more.")
            self.waiting_step += 1

        elif current_idx >= len(current_data):
            log.debug("Entering waiting mode.")
            self.step += 1
            self.idx = 0
            self.waiting = True
        log.debug("current index %s" % current_idx)
        log.debug("current data %s" % len(current_data))
        return True

    def get_mutation(self, step):
        """
        Returns the current packet to be sent to the wire.
        If no mutation is necessary it will return the plain data.
        Should be called when you are interested in obtaining the data to be
        sent for the selected state.

        @param step: the current step you want the mutation for

        returns the mutated packet for the specified step.
        """
        if step != self.step or self.waiting:
            log.debug("I am not going to do anything :)")
            return self.steps[step]['data']

        data = self.steps[step]['data']
        print "Mutating %s with idx %s" % (data, self.idx)
        return self._mutate(data, self.idx)

