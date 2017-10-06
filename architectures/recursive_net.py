import torch
import torch.nn as nn
import torch.nn.functional as F

from .batching import pad_batch, batch

class GRNNTransformSimple(nn.Module):
    def __init__(self, n_features, n_hidden):
        super().__init__()
        self.fc_u = nn.Linear(n_features, n_hidden)
        self.fc_h = nn.Linear(3 * n_hidden, n_hidden)

    def forward(self, jets):
        levels, children, n_inners, contents = batch(jets)
        n_levels = len(levels)
        embeddings = []


        for i, nodes in enumerate(levels[::-1]):
            j = n_levels - 1 - i
            try:
                inner = nodes[:n_inners[j]]
            except ValueError:
                inner = []
            try:
                outer = nodes[n_inners[j]:]
            except ValueError:
                outer = []

            u_k = F.tanh(self.fc_u(contents[j]))

            if len(inner) > 0:
                zero = torch.zeros(1).long(); one = torch.ones(1).long()
                if torch.cuda.is_available(): zero = zero.cuda(); one = one.cuda()
                h_L = embeddings[-1][children[inner, zero]]
                h_R = embeddings[-1][children[inner, one]]
                h = F.tanh(
                        self.fc_h(
                            torch.cat(
                                (h_L, h_R, u_k[:n_inners[j]]), 1
                            )
                        )
                    )

                try:
                    embeddings.append(torch.cat((h, u_k[n_inners[j]:]), 0))
                except ValueError:
                    embeddings.append(h)

            else:
                embeddings.append(u_k)

        return embeddings[-1].view((len(jets), -1))


class GRNNTransformGated(nn.Module):
    def __init__(self, n_features, n_hidden):
        super().__init__()
        self.n_hidden = n_hidden
        self.n_features = n_features
        self.fc_u = nn.Linear(n_features, n_hidden)
        self.fc_h = nn.Linear(3 * n_hidden, n_hidden)
        self.fc_z = nn.Linear(4 * n_hidden, 4 * n_hidden)
        self.fc_r = nn.Linear(3 * n_hidden, 3 * n_hidden)

    def forward(self, jets, return_states=False):


        levels, children, n_inners, contents = batch(jets)

        states = {"embeddings": [], "z": [], "r": [], "levels": levels,
                    "children": children, "n_inners": n_inners}

        embeddings = []

        states = self.up_the_tree(states, embeddings, levels, children, n_inners, contents)

        if return_states:
            return states
        else:
            return embeddings[-1].view((len(jets), -1))


    def up_the_tree(self, states, embeddings, levels, children, n_inners, contents):
        n_levels = len(levels)
        n_hidden = self.n_hidden

        for i, nodes in enumerate(levels[::-1]):
            j = n_levels - 1 - i
            try:
                inner = nodes[:n_inners[j]]
            except ValueError:
                inner = []
            try:
                outer = nodes[n_inners[j]:]
            except ValueError:
                outer = []

            u_k = F.tanh(self.fc_u(contents[j]))

            if len(inner) > 0:
                try:
                    u_k_inners = u_k[:n_inners[j]]
                except ValueError:
                    u_k_inners = []
                try:
                    u_k_leaves = u_k[n_inners[j]:]
                except ValueError:
                    u_k_leaves = []

                zero = torch.zeros(1).long(); one = torch.ones(1).long()
                if torch.cuda.is_available(): zero = zero.cuda(); one = one.cuda()
                h_L = embeddings[-1][children[inner, zero]]
                h_R = embeddings[-1][children[inner, one]]

                hhu = torch.cat((h_L, h_R, u_k_inners), 1)
                r = F.sigmoid(self.fc_r(hhu))
                h_H = F.tanh(self.fc_h(r * hhu))

                z = self.fc_z(torch.cat((h_H, hhu), -1))
                z_H = z[:, :n_hidden]               # new activation
                z_L = z[:, n_hidden:2*n_hidden]     # left activation
                z_R = z[:, 2*n_hidden:3*n_hidden]   # right activation
                z_N = z[:, 3*n_hidden:]             # local state
                z = torch.stack([z_H,z_L,z_R,z_N], 2)
                z = F.softmax(z)

                h = ((z[:, :, 0] * h_H) +
                     (z[:, :, 1] * h_L) +
                     (z[:, :, 2] * h_R) +
                     (z[:, :, 3] * u_k_inners))

                try:
                    embeddings.append(torch.cat((h, u_k_leaves), 0))
                except AttributeError:
                    embeddings.append(h)
                states["embeddings"].append(embeddings[-1])
                states["z"].append(z)
                states["r"].append(r)

            else:
                embeddings.append(u_k)

                states["embeddings"].append(embeddings[-1])

    def down_the_tree(self, states, embeddings, levels, children, n_inners, contents):
        n_levels = len(levels)
        n_hidden = self.n_hidden

        for j, nodes in enumerate(levels):

            try:
                inner = nodes[:n_inners[j]]
            except ValueError:
                inner = []
            try:
                outer = nodes[n_inners[j]:]
            except ValueError:
                outer = []

            u_k = F.tanh(self.fc_u(contents[j]))

            if len(inner) > 0:
                try:
                    u_k_inners = u_k[:n_inners[j]]
                except ValueError:
                    u_k_inners = []
                try:
                    u_k_leaves = u_k[n_inners[j]:]
                except ValueError:
                    u_k_leaves = []

                zero = torch.zeros(1).long(); one = torch.ones(1).long()
                if torch.cuda.is_available(): zero = zero.cuda(); one = one.cuda()
                h_L = embeddings[-1][children[inner, zero]]
                h_R = embeddings[-1][children[inner, one]]

                hhu = torch.cat((h_L, h_R, u_k_inners), 1)
                r = F.sigmoid(self.fc_r(hhu))
                h_H = F.tanh(self.fc_h(r * hhu))

                z = self.fc_z(torch.cat((h_H, hhu), -1))
                z_H = z[:, :n_hidden]               # new activation
                z_L = z[:, n_hidden:2*n_hidden]     # left activation
                z_R = z[:, 2*n_hidden:3*n_hidden]   # right activation
                z_N = z[:, 3*n_hidden:]             # local state
                z = torch.stack([z_H,z_L,z_R,z_N], 2)
                z = F.softmax(z)

                h = ((z[:, :, 0] * h_H) +
                     (z[:, :, 1] * h_L) +
                     (z[:, :, 2] * h_R) +
                     (z[:, :, 3] * u_k_inners))

                try:
                    embeddings.append(torch.cat((h, u_k_leaves), 0))
                except AttributeError:
                    embeddings.append(h)
                states["embeddings"].append(embeddings[-1])
                states["z"].append(z)
                states["r"].append(r)

            else:
                embeddings.append(u_k)

                states["embeddings"].append(embeddings[-1])